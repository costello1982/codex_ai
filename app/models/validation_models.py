"""Validation result models."""
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    severity: str
    message: str


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
