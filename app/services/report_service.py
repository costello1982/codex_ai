"""Build markdown reports and package artifacts."""
from __future__ import annotations

from pathlib import Path

from app.models.design_models import FabricDesign
from app.models.validation_models import ValidationResult
from app.utils.yaml_utils import dump_yaml


class ReportService:
    def write_outputs(
        self,
        design: FabricDesign,
        configs: dict[str, str],
        validation: ValidationResult,
        topology_dot: str,
        topology_image: str | None,
        output_dir: Path,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "configs").mkdir(exist_ok=True)
        (output_dir / "design.yaml").write_text(dump_yaml(design.model_dump(mode="json")), encoding="utf-8")
        (output_dir / "design_summary.md").write_text(
            f"# Design Summary\n\nFabric: {design.fabric_name}\n\nSpines: {design.spine_count}\nLeaf roles total: {len(design.devices)-design.spine_count}\n",
            encoding="utf-8",
        )
        (output_dir / "assumptions.md").write_text("\n".join(f"- {x}" for x in design.assumptions), encoding="utf-8")
        (output_dir / "warnings.md").write_text("\n".join(f"- {x}" for x in design.warnings) or "- None", encoding="utf-8")
        (output_dir / "validation_report.md").write_text(
            "\n".join([f"- {i.severity}: {i.message}" for i in validation.issues]) or "- valid",
            encoding="utf-8",
        )
        (output_dir / "topology.dot").write_text(topology_dot, encoding="utf-8")
        if topology_image:
            (output_dir / "topology_image.txt").write_text(topology_image, encoding="utf-8")
        for name, cfg in configs.items():
            (output_dir / "configs" / f"{name}.cfg").write_text(cfg, encoding="utf-8")
