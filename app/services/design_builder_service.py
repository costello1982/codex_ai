"""Build normalized fabric design from intent + policies."""
from __future__ import annotations

from app.models.design_models import (
    Device,
    DeviceRole,
    DciInterconnect,
    FabricDesign,
    RequirementIntent,
    SiteDesign,
    Tenant,
    Vrf,
    Layer2Segment,
)


class DesignBuilderService:
    def build(self, intent: RequirementIntent) -> FabricDesign:
        vpc_leafs = intent.vpc_pair_count * 2
        regular_leafs = max(intent.total_leaf_count - intent.border_leaf_count - vpc_leafs, 0)
        design = FabricDesign(
            fabric_name=intent.fabric_name,
            site=SiteDesign(site_name=intent.site_name, site_id=intent.site_id or 101, underlay_protocol=intent.underlay_protocol),
            spine_count=intent.spine_count,
            regular_leaf_count=regular_leafs,
            border_leaf_count=intent.border_leaf_count,
            vpc_pair_count=intent.vpc_pair_count,
            interconnect=DciInterconnect(enabled=intent.interconnect_requested, mode="evpn_dci" if intent.interconnect_requested else "none", remote_site_name="dc2" if intent.interconnect_requested else None),
            assumptions=[
                "site_id defaulted to 101" if intent.site_id is None else "site_id user-provided",
                "overlay_asn defaulted from policy" if intent.overlay_asn is None else "overlay_asn user-provided",
            ],
            warnings=intent.warnings,
        )
        design.tenants = [
            Tenant(
                name="Tenant-A",
                vrfs=[Vrf(name="VRF-A", l3vni=design.allocation_pools.l3vni_start)],
                l2_segments=[Layer2Segment(name="WEB", vlan_id=design.allocation_pools.vlan_start, vni=design.allocation_pools.l2vni_start, gateway="10.10.10.1/24")],
            )
        ]
        node = 1
        for i in range(design.spine_count):
            design.devices.append(Device(name=f"spine{i+1}", role=DeviceRole.SPINE, node_id=node))
            node += 1
        for i in range(design.border_leaf_count):
            design.devices.append(Device(name=f"bl{i+1}", role=DeviceRole.BORDER_LEAF, node_id=node, site_id=design.site.site_id))
            node += 1
        for i in range(design.vpc_pair_count):
            design.devices.append(Device(name=f"vpc{i+1}a", role=DeviceRole.VPC_LEAF_PRIMARY, node_id=node))
            node += 1
            design.devices.append(Device(name=f"vpc{i+1}b", role=DeviceRole.VPC_LEAF_SECONDARY, node_id=node))
            node += 1
        for i in range(design.regular_leaf_count):
            design.devices.append(Device(name=f"leaf{i+1}", role=DeviceRole.LEAF, node_id=node))
            node += 1
        return design
