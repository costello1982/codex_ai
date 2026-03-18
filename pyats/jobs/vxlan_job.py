"""pyATS job file for NX-OS VXLAN EVPN validations."""

from pyats.easypy import run


def main(runtime):
    run(testscript="pyats/tests/test_vxlan_evpn.py", testbed=runtime.testbed)
