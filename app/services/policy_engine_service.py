"""Policy enforcement layer."""
from __future__ import annotations

from app.models.design_models import DeviceRole, FabricDesign


class PolicyEngineService:
    def apply(self, design: FabricDesign) -> FabricDesign:
        if design.interconnect.enabled and not any(d.role == DeviceRole.BORDER_LEAF for d in design.devices):
            raise ValueError("Inter-site interconnect requires at least one border leaf")
        if design.vpc_pair_count > 0:
            primary = [d for d in design.devices if d.role == DeviceRole.VPC_LEAF_PRIMARY]
            secondary = [d for d in design.devices if d.role == DeviceRole.VPC_LEAF_SECONDARY]
            if len(primary) != len(secondary):
                raise ValueError("vPC primary/secondary counts must match")
        return design
