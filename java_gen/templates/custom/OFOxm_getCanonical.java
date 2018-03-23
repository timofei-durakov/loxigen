//:: import re
    public ${prop.java_type.public_type} getCanonical() {
        //:: if not msg.member_by_name("masked").value == "true":
        // exact match OXM is always canonical
        return this;
        //:: elif version.ir_version.short_constant == 'OF_1_2':
        // Skip canonicalisation due to issues with Accton based switches. This switches treat
        // all "exact" match as masked match with zero mask. That lead to incorrect packets matching.
        // As workaround masked match with ZERO_MASK is used.
        return this;
        //:: else:
        //:: mask_type = msg.member_by_name("mask").java_type.public_type
        if (${mask_type}.NO_MASK.equals(mask)) {
            //:: unmasked = re.sub(r'(.*)Masked(Ver.*)', r'\1\2', msg.name)
            return new ${unmasked}(value);
        } else if(${mask_type}.FULL_MASK.equals(mask)) {
            return null;
        } else {
            return this;
        }
        //:: #endif
    }
