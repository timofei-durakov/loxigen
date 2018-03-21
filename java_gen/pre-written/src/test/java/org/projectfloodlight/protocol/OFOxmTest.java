package org.projectfloodlight.protocol;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertThat;
import static org.junit.Assert.assertTrue;

import org.hamcrest.CoreMatchers;
import org.junit.Before;
import org.junit.Test;
import org.projectfloodlight.openflow.protocol.OFFactories;
import org.projectfloodlight.openflow.protocol.OFVersion;
import org.projectfloodlight.openflow.protocol.oxm.OFOxm;
import org.projectfloodlight.openflow.protocol.oxm.OFOxmIpv4Src;
import org.projectfloodlight.openflow.protocol.oxm.OFOxmIpv4SrcMasked;
import org.projectfloodlight.openflow.protocol.oxm.OFOxms;
import org.projectfloodlight.openflow.types.IPv4Address;
import org.projectfloodlight.openflow.types.IPv4AddressWithMask;

public class OFOxmTest {
    private OFOxms oF13oxms;
    private OFOxms oF12oxms;

    @Before
    public void setup() {
        oF12oxms = OFFactories.getFactory(OFVersion.OF_12).oxms();
        oF13oxms = OFFactories.getFactory(OFVersion.OF_13).oxms();
    }

    @Test
    public void testOF12GetCanonicalFullMask() {
        IPv4AddressWithMask empty = IPv4AddressWithMask.of("0.0.0.0/0");
        assertEquals(IPv4Address.FULL_MASK, empty.getMask());
        OFOxmIpv4SrcMasked ipv4SrcMasked = oF12oxms.ipv4SrcMasked(empty.getValue(), empty.getMask());
        // OF12 getCanonical() must not change anything
        assertEquals(ipv4SrcMasked.getCanonical(), ipv4SrcMasked);
    }

    @Test
    public void testOF13GetCanonicalFullMask() {
        IPv4AddressWithMask empty = IPv4AddressWithMask.of("0.0.0.0/0");
        assertEquals(IPv4Address.FULL_MASK, empty.getMask());
        OFOxmIpv4SrcMasked ipv4SrcMasked = oF13oxms.ipv4SrcMasked(empty.getValue(), empty.getMask());
        // canonicalize should remove /0
        assertNull(ipv4SrcMasked.getCanonical());
    }

    @Test
    public void testOF12GetCanonicalNoMask() {
        IPv4AddressWithMask fullIp = IPv4AddressWithMask.of("1.2.3.4/32");
        assertEquals(IPv4Address.NO_MASK, fullIp.getMask());
        OFOxmIpv4SrcMasked ipv4SrcMasked = oF13oxms.ipv4SrcMasked(fullIp.getValue(), fullIp.getMask());
        assertTrue(ipv4SrcMasked.isMasked());
        assertEquals(IPv4Address.NO_MASK, ipv4SrcMasked.getMask());

        // OF12 getCanonical() must not change anything
        OFOxm<IPv4Address> canonical = ipv4SrcMasked.getCanonical();
        assertThat(canonical, CoreMatchers.instanceOf(OFOxmIpv4SrcMasked.class));
        assertTrue(canonical.isMasked());
        assertEquals(IPv4Address.NO_MASK, canonical.getMask());
    }

    @Test
    public void testOF13GetCanonicalNoMask() {
        IPv4AddressWithMask fullIp = IPv4AddressWithMask.of("1.2.3.4/32");
        assertEquals(IPv4Address.NO_MASK, fullIp.getMask());
        OFOxmIpv4SrcMasked ipv4SrcMasked = oF13oxms.ipv4SrcMasked(fullIp.getValue(), fullIp.getMask());
        assertTrue(ipv4SrcMasked.isMasked());
        assertEquals(IPv4Address.NO_MASK, ipv4SrcMasked.getMask());

        // canonicalize should convert the masked oxm to the non-masked one
        OFOxm<IPv4Address> canonical = ipv4SrcMasked.getCanonical();
        assertThat(canonical, CoreMatchers.instanceOf(OFOxmIpv4Src.class));
        assertFalse(canonical.isMasked());
    }

    @Test
    public void testGetCanonicalNormalMask() {
        IPv4AddressWithMask ip = IPv4AddressWithMask.of("1.2.3.0/24");
        OFOxmIpv4SrcMasked ipv4SrcMasked = oF13oxms.ipv4SrcMasked(ip.getValue(), ip.getMask());
        assertTrue(ipv4SrcMasked.isMasked());

        // canonicalize should convert the masked oxm to the non-masked one
        OFOxm<IPv4Address> canonical = ipv4SrcMasked.getCanonical();
        assertEquals(ipv4SrcMasked, canonical);
    }
}
