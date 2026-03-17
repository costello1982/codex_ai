"""Design validation checks."""
from __future__ import annotations

from app.models.design_models import FabricDesign
from app.models.validation_models import ValidationIssue, ValidationResult


class ValidationService:
    def validate(self, design: FabricDesign) -> ValidationResult:
        issues: list[ValidationIssue] = []
        loopbacks = [d.loopback0 for d in design.devices if d.loopback0]
        if len(loopbacks) != len(set(loopbacks)):
            issues.append(ValidationIssue(severity="error", message="Duplicate loopback allocation detected"))
        vlans = [seg.vlan_id for t in design.tenants for seg in t.l2_segments]
        if len(vlans) != len(set(vlans)):
            issues.append(ValidationIssue(severity="error", message="Duplicate VLAN IDs detected"))
        return ValidationResult(valid=not any(i.severity == "error" for i in issues), issues=issues)
