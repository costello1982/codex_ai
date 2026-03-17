"""Output artifact model."""
from pydantic import BaseModel, Field


class GeneratedArtifacts(BaseModel):
    design_yaml: str
    topology_dot: str
    topology_image: str | None = None
    configs: dict[str, str] = Field(default_factory=dict)
    reports: dict[str, str] = Field(default_factory=dict)
