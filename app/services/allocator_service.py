"""Deterministic allocation engine."""
from __future__ import annotations

from ipaddress import ip_network

from app.models.design_models import DeviceRole, FabricDesign, UnderlayLink, VpcPair


class AllocatorService:
    def allocate(self, design: FabricDesign) -> FabricDesign:
        loop_pool = list(ip_network(design.allocation_pools.loopback_pool).hosts())
        p2p_pool = list(ip_network(design.allocation_pools.p2p_pool).subnets(new_prefix=31))
        idx = 0
        for device in design.devices:
            device.loopback0 = f"{loop_pool[idx]}/32"
            device.router_id = str(loop_pool[idx])
            device.asn = design.allocation_pools.overlay_asn if device.role != DeviceRole.SPINE else design.allocation_pools.spine_asn
            idx += 1

        link_idx = 0
        leaves = [d for d in design.devices if d.role != DeviceRole.SPINE]
        spines = [d for d in design.devices if d.role == DeviceRole.SPINE]
        for leaf in leaves:
            for spine in spines:
                subnet = p2p_pool[link_idx]
                ips = list(subnet.hosts())
                design.underlay_links.append(
                    UnderlayLink(
                        local_device=leaf.name,
                        local_intf=f"Ethernet1/{spine.node_id}",
                        local_ip=f"{ips[0]}/31",
                        peer_device=spine.name,
                        peer_intf=f"Ethernet1/{leaf.node_id}",
                        peer_ip=f"{ips[1]}/31",
                    )
                )
                link_idx += 1

        primaries = [d for d in design.devices if d.role == DeviceRole.VPC_LEAF_PRIMARY]
        secondaries = [d for d in design.devices if d.role == DeviceRole.VPC_LEAF_SECONDARY]
        for i, (p, s) in enumerate(zip(primaries, secondaries), start=1):
            design.vpc_pairs.append(VpcPair(primary=p.name, secondary=s.name, domain_id=100 + i))
            p.vpc_domain_id = s.vpc_domain_id = 100 + i
        return design
