# Copyright 2013, Big Switch Networks, Inc.
#
# LoxiGen is licensed under the Eclipse Public License, version 1.0 (EPL), with
# the following special exception:
#
# LOXI Exception
#
# As a special exception to the terms of the EPL, you may distribute libraries
# generated by LoxiGen (LoxiGen Libraries) under the terms of your choice, provided
# that copyright and licensing notices generated by LoxiGen are not altered or removed
# from the LoxiGen Libraries and the notice provided below is (i) included in
# the LoxiGen Libraries, if distributed in source code form and (ii) included in any
# documentation for the LoxiGen Libraries, if distributed in binary form.
#
# Notice: "Copyright 2013, Big Switch Networks, Inc. This library was generated by the LoxiGen Compiler."
#
# You may not use this file except in compliance with the EPL or LOXI Exception. You may obtain
# a copy of the EPL at:
#
# http://www.eclipse.org/legal/epl-v10.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# EPL for the specific language governing permissions and limitations
# under the EPL.

import sys

import re
import string
import os
import glob
import copy
import collections
import c_gen.of_g_legacy as of_g
import c_gen.type_maps as type_maps
import c_gen.loxi_utils_legacy as loxi_utils
import loxi_globals
import c_gen.identifiers as identifiers
import pyparsing
import loxi_front_end.parser as parser
import c_gen.translation as translation
import loxi_front_end.frontend as frontend
from loxi_ir import *
from generic_utils import *

root_dir = os.path.dirname(os.path.realpath(__file__))

versions = {}
# TODO:  Put these in a class so they get documented

## Dict indexed by version giving all info related to version
#
# This is local; after processing, the information is stored in
# of_g variables.

def add_class(wire_version, cls, members):
    """
    Process a class for the given version and update the unified
    list of classes as needed.

    @param wire_version The wire version for this class defn
    @param cls The name of the class being added
    @param members The list of members with offsets calculated
    """
    memid = 0

    sig = loxi_utils.class_signature(members)
    if cls in of_g.unified:
        uc = of_g.unified[cls]
        if wire_version in uc:
            debug("Error adding %s to unified. Wire ver %d exists" %
                  (cls, wire_version))
            sys.exit(1)
        uc[wire_version] = {}
        # Check for a matching signature
        for wver in uc:
            if type(wver) != type(0): continue
            if wver == wire_version: continue
            if not "use_version" in uc[wver]:
                if sig == loxi_utils.class_signature(uc[wver]["members"]):
                    log("Matched %s, ver %d to ver %d" %
                          (cls, wire_version, wver))
                    # have a match with existing version
                    uc[wire_version]["use_version"] = wver
                    # What else to do?
                    return
    else:  # Haven't seen this entry before
        log("Adding %s to unified list, ver %d" % (cls, wire_version))
        of_g.unified[cls] = dict(union={})
        uc = of_g.unified[cls]

    # At this point, need to add members for this version
    uc[wire_version] = dict(members = members)

    # Per member processing:
    #  Add to union list (I'm sure there's a better way)
    #  Check if it's a list
    union = uc["union"]
    if not cls in of_g.ordered_members:
        of_g.ordered_members[cls] = []
    for member in members:
        m_name = member["name"]
        m_type = member["m_type"]
        if m_name.find("pad") == 0:
            continue
        if m_name in union:
            if not m_type == union[m_name]["m_type"]:
                debug("ERROR:   CLASS: %s. VERSION %d. MEMBER: %s. TYPE: %s" %
                      (cls, wire_version, m_name, m_type))
                debug("    Type conflict adding member to unified set.")
                debug("    Current union[%s]:" % m_name)
                debug(union[m_name])
                sys.exit(1)
        else:
            union[m_name] = dict(m_type=m_type, memid=memid)
            memid += 1
        if not m_name in of_g.ordered_members[cls]:
            of_g.ordered_members[cls].append(m_name)

def order_and_assign_object_ids():
    """
    Order all classes and assign object ids to all classes.

    This is done to promote a reasonable order of the objects, putting
    messages first followed by non-messages.  No assumptions should be
    made about the order, nor about contiguous numbering.  However, the
    numbers should all be reasonably small allowing arrays indexed by
    these enum values to be defined.
    """

    # Generate separate message and non-message ordered lists
    for cls in of_g.unified:
        if loxi_utils.class_is_message(cls):
            of_g.ordered_messages.append(cls)
        elif loxi_utils.class_is_list(cls):
            of_g.ordered_list_objects.append(cls)
        else:
            of_g.ordered_non_messages.append(cls)

    of_g.ordered_messages.sort()
    of_g.ordered_pseudo_objects.sort()
    of_g.ordered_non_messages.sort()
    of_g.ordered_list_objects.sort()
    of_g.standard_class_order.extend(of_g.ordered_messages)
    of_g.standard_class_order.extend(of_g.ordered_non_messages)
    of_g.standard_class_order.extend(of_g.ordered_list_objects)

    # This includes pseudo classes for which most code is not generated
    of_g.all_class_order.extend(of_g.ordered_messages)
    of_g.all_class_order.extend(of_g.ordered_non_messages)
    of_g.all_class_order.extend(of_g.ordered_list_objects)
    of_g.all_class_order.extend(of_g.ordered_pseudo_objects)

    # Assign object IDs
    for cls in of_g.ordered_messages:
        of_g.unified[cls]["object_id"] = of_g.object_id
        of_g.object_id += 1
    for cls in of_g.ordered_non_messages:
        of_g.unified[cls]["object_id"] = of_g.object_id
        of_g.object_id += 1
    for cls in of_g.ordered_list_objects:
        of_g.unified[cls]["object_id"] = of_g.object_id
        of_g.object_id += 1


def initialize_versions():
    """
    Create an empty datastructure for each target version.
    """

    for version in loxi_globals.OFVersions.target_versions:
        wire_version = version.wire_version
        long_constant = version.constant_version('OF_VERSION_')
        of_g.wire_ver_map[wire_version] = long_constant
        of_g.short_version_names[wire_version] = version.short_constant
        of_g.of_version_range.append(wire_version)
        of_g.of_version_wire2name[wire_version] = long_constant
        versions[long_constant] = dict(
            version_name = version.constant,
            wire_version = wire_version,
            classes = {})
        of_g.ordered_classes[wire_version] = []

    of_g.target_version_list = [ v.wire_version for v in loxi_globals.OFVersions.target_versions ]

def build_ordered_classes():
    """
    Read in from files given on command line and update global state

    @fixme Should select versions to support from command line
    """

    for version, protocol in loxi_globals.ir.items():
        wire_version = version.wire_version
        # Populate global state
        version_name = of_g.of_version_wire2name[wire_version]

        for ofclass in protocol.classes:
            of_g.ordered_classes[wire_version].append(ofclass.name)
            legacy_members = []
            pad_count = 0
            for m in ofclass.members:
                if type(m) == OFPadMember:
                    continue
                else:
                    if m.oftype.find("list(") == 0:
                        (list_name, base_type) = loxi_utils.list_name_extract(m.oftype)
                        m_type = list_name + "_t"
                    else:
                        enum = find(lambda e: e.name == m.oftype, protocol.enums)
                        if enum and "wire_type" in enum.params:
                            m_type = enum.params["wire_type"]
                        else:
                            m_type = m.oftype

                    if m.offset is None:
                        m_offset = -1
                    else:
                        m_offset = m.offset

                    legacy_members.append(dict(m_type=m_type, name=m.name, offset=m_offset))
            versions[version_name]['classes'][ofclass.name] = legacy_members

            of_g.base_length[(ofclass.name, version.wire_version)] = ofclass.base_length
            if ofclass.is_fixed_length:
                of_g.is_fixed_length.add((ofclass.name, version.wire_version))

        for enum in protocol.enums:
            for entry in enum.entries:
                identifiers.add_identifier(
                    translation.loxi_name(entry.name),
                    entry.name, enum.name, entry.value, wire_version,
                    of_g.identifiers, of_g.identifiers_by_group)

def populate_type_maps():
    """
    Use the type members in the IR to fill out the legacy type_maps.
    """
    type_maps.generate_maps()

def analyze_input():
    """
    Add information computed from the input, including offsets and
    lengths of struct members and the set of list and action_id types.
    """
    # Create lists
    for version, protocol in loxi_globals.ir.items():
        lists = set()
        classes = versions[of_g.of_version_wire2name[version.wire_version]]['classes']

        for ofclass in protocol.classes:
            for m in ofclass.members:
                if isinstance(m, OFDataMember) and m.oftype.find("list(") == 0:
                    (list_name, base_type) = loxi_utils.list_name_extract(m.oftype)
                    lists.add(list_name)

        for list_type in lists:
            classes[list_type] = []
            of_g.ordered_classes[version.wire_version].append(list_type)
            of_g.base_length[(list_type, version.wire_version)] = 0

    # Find special offsets
    # These are defined as members (except padding) that don't have a fixed
    # offset. The special_offsets map stores the name of the previous member.
    for version, protocol in loxi_globals.ir.items():
        for ofclass in protocol.classes:
            prev_member = None
            for m in ofclass.members:
                if isinstance(m, OFPadMember):
                    continue
                if m.offset == None:
                    old = of_g.special_offsets.get((ofclass.name, m.name))
                    if old and old != prev_member.name:
                        raise Exception("Error: special offset changed: version=%s cls=%s member=%s old=%s new=%s" %
                                        (version, ofclass.name, m.name, old, prev_member.name))
                    of_g.special_offsets[(ofclass.name, m.name)] = prev_member.name
                prev_member = m

def unify_input():
    """
    Create Unified View of Objects
    """

    global versions

    # Add classes to unified in wire-format order so that it is easier
    # to generate things later
    keys = list(versions.keys())
    keys.sort(reverse=True)
    for version in keys:
        wire_version = versions[version]["wire_version"]
        classes = versions[version]["classes"]
        for cls in of_g.ordered_classes[wire_version]:
            add_class(wire_version, cls, classes[cls])
