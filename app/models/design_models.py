"""Primary design data models."""
from __future__ import annotations

from enum import Enum
from ipaddress import ip_network
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DeviceRole(str, Enum):
    SPINE = "spine"
    LEAF = "leaf"
    BORDER_LEAF = "border_leaf"
    VPC_LEAF_PRIMARY = "vpc_leaf_primary"
    VPC_LEAF_SECONDARY = "vpc_leaf_secondary"


class UnderlayProtocol(str, Enum):
    OSPF = "ospf"
    ISIS = "isis"
    EBGP = "ebgp"


class InterconnectMode(str, Enum):
    NONE = "none"
    EVPN_DCI = "evpn_dci"


class AllocationPools(BaseModel):
    loopback_pool: str = "10.255.0.0/24"
    p2p_pool: str = "10.254.0.0/24"
    anycast_gateway_mac: str = "0001.0001.0001"
    vlan_start: int = 100
    l2vni_start: int = 10100
    l3vni_start: int = 20100
    overlay_asn: int = 65000
    spine_asn: int = 65100


class Layer2Segment(BaseModel):
    name: str
    vlan_id: int
    vni: int
    gateway: str


class Vrf(BaseModel):
    name: str
    l3vni: int


class Tenant(BaseModel):
    name: str
    vrfs: list[Vrf] = Field(default_factory=list)
    l2_segments: list[Layer2Segment] = Field(default_factory=list)


class DciInterconnect(BaseModel):
    enabled: bool = False
    remote_site_name: str | None = None
    mode: InterconnectMode = InterconnectMode.NONE


class Device(BaseModel):
    name: str
    role: DeviceRole
    node_id: int
    router_id: str | None = None
    loopback0: str | None = None
    asn: int | None = None
    site_id: int | None = None
    vpc_domain_id: int | None = None


class UnderlayLink(BaseModel):
    local_device: str
    local_intf: str
    local_ip: str
    peer_device: str
    peer_intf: str
    peer_ip: str


class VpcPair(BaseModel):
    primary: str
    secondary: str
    domain_id: int
    peer_link_port_channel: int = 10


class SiteDesign(BaseModel):
    site_name: str
    site_id: int
    underlay_protocol: UnderlayProtocol = UnderlayProtocol.EBGP


class FabricDesign(BaseModel):
    fabric_name: str
    site: SiteDesign
    spine_count: int
    regular_leaf_count: int
    border_leaf_count: int
    vpc_pair_count: int = 1
    interconnect: DciInterconnect = Field(default_factory=DciInterconnect)
    allocation_pools: AllocationPools = Field(default_factory=AllocationPools)
    devices: list[Device] = Field(default_factory=list)
    underlay_links: list[UnderlayLink] = Field(default_factory=list)
    vpc_pairs: list[VpcPair] = Field(default_factory=list)
    tenants: list[Tenant] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "FabricDesign":
        if self.spine_count < 2:
            raise ValueError("At least two spines are required")
        total_leafs = self.regular_leaf_count + self.border_leaf_count + (self.vpc_pair_count * 2)
        if total_leafs <= 0:
            raise ValueError("At least one leaf role must exist")
        return self


class RequirementIntent(BaseModel):
    fabric_name: str = "fab1"
    site_name: str = "dc1"
    site_id: int | None = None
    spine_count: int
    total_leaf_count: int
    border_leaf_count: int = 0
    vpc_pair_count: int = 0
    interconnect_requested: bool = False
    underlay_protocol: UnderlayProtocol = UnderlayProtocol.EBGP
    overlay_asn: int | None = None
    tenant_count: int = 1
    missing_parameters: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DesignWarnings(BaseModel):
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
