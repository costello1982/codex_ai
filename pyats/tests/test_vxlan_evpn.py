"""pyATS/Genie validation for NX-OS VXLAN EVPN fabric."""

from __future__ import annotations

from pyats import aetest


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_devices(self, testbed):
        testbed.connect(log_stdout=False)
        self.parent.parameters["testbed"] = testbed


class ValidateUnderlay(aetest.Testcase):
    @aetest.test
    def ospf_neighbors_full(self, testbed):
        for device in testbed.devices.values():
            parsed = device.parse("show ip ospf neighbors")
            self.assertTrue(
                parsed.get("interfaces"),
                f"No OSPF neighbors found on {device.name}",
            )


class ValidateOverlay(aetest.Testcase):
    @aetest.test
    def evpn_bgp_established(self, testbed):
        for device in testbed.devices.values():
            parsed = device.parse("show bgp l2vpn evpn summary")
            vrf_data = parsed.get("vrf", {})
            self.assertTrue(vrf_data, f"No EVPN BGP data on {device.name}")


class ValidateNve(aetest.Testcase):
    @aetest.test
    def nve_peers_up(self, testbed):
        for device in testbed.devices.values():
            if "spine" in device.alias:
                continue
            parsed = device.parse("show nve peers")
            self.assertTrue(parsed.get("nve_peers"), f"No NVE peers on {device.name}")


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect(self, testbed):
        testbed.disconnect()


if __name__ == "__main__":
    aetest.main()
