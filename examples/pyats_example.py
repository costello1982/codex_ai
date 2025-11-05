"""Minimal pyATS aetest script for NX-OS validation."""

from __future__ import annotations

from pyats import aetest
from genie.testbed import load


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_devices(self, testbed):
        self.parent.parameters.update(testbed=testbed)
        for device in testbed:
            device.connect(log_stdout=False)


class VerifyInterfaceState(aetest.Testcase):
    @aetest.setup
    def load_testbed(self, testbed):
        self.testbed = load(testbed) if isinstance(testbed, str) else testbed

    @aetest.test
    def check_interfaces(self):
        for device in self.testbed:
            parsed = device.parse("show interface status")
            down_interfaces = [
                name
                for name, data in parsed.items()
                if data.get("status") != "connected" and not name.startswith("mgmt")
            ]
            self.passed(f"{device.name}: all interfaces up") if not down_interfaces else self.failed(
                f"{device.name}: down interfaces {down_interfaces}"
            )


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect(self, steps, testbed):
        for device in testbed:
            with steps.start(f"Disconnect {device.name}"):
                device.disconnect()


if __name__ == "__main__":
    aetest.main(testbed="testbed.yaml")
