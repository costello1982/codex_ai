"""Generation routes for configs/topology/reports."""
from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings
from app.models.design_models import FabricDesign
from app.services.config_renderer_service import ConfigRendererService
from app.services.report_service import ReportService
from app.services.topology_service import TopologyService
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/all")
def generate(payload: dict) -> dict:
    design = FabricDesign.model_validate(payload["design"])
    output_dir = settings.outputs_dir / design.fabric_name
    configs = ConfigRendererService().render(design)
    dot, image, _ = TopologyService().render(design, output_dir)
    validation = ValidationService().validate(design)
    ReportService().write_outputs(design, configs, validation, dot, image, output_dir)
    return {"output_dir": str(output_dir), "configs": list(configs.keys()), "validation": validation.model_dump()}
