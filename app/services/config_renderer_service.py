"""Deterministic configuration renderer."""
from __future__ import annotations

from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.models.design_models import DeviceRole, FabricDesign


class ConfigRendererService:
    def __init__(self) -> None:
        self.env = Environment(loader=FileSystemLoader(settings.templates_dir))

    def render(self, design: FabricDesign) -> dict[str, str]:
        role_tpl = {
            DeviceRole.SPINE: "nxos/spine.j2",
            DeviceRole.LEAF: "nxos/leaf.j2",
            DeviceRole.BORDER_LEAF: "nxos/border_leaf.j2",
            DeviceRole.VPC_LEAF_PRIMARY: "nxos/vpc_leaf_primary.j2",
            DeviceRole.VPC_LEAF_SECONDARY: "nxos/vpc_leaf_secondary.j2",
        }
        output: dict[str, str] = {}
        for device in design.devices:
            template = self.env.get_template(role_tpl[device.role])
            links = [l for l in design.underlay_links if l.local_device == device.name]
            output[device.name] = template.render(device=device, design=design, links=links)
        return output
