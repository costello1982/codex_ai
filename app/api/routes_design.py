"""Requirement parsing and design construction routes."""
from fastapi import APIRouter

from app.services.allocator_service import AllocatorService
from app.services.design_builder_service import DesignBuilderService
from app.services.policy_engine_service import PolicyEngineService
from app.services.requirement_parser_service import RequirementParserService
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/design", tags=["design"])


@router.post("/parse")
def parse_requirements(payload: dict) -> dict:
    text = payload.get("requirements", "")
    intent = RequirementParserService().parse(text)
    return intent.model_dump(mode="json")


@router.post("/build")
def build_design(payload: dict) -> dict:
    text = payload.get("requirements", "")
    parser = RequirementParserService()
    builder = DesignBuilderService()
    policy = PolicyEngineService()
    allocator = AllocatorService()
    validator = ValidationService()

    intent = parser.parse(text)
    design = builder.build(intent)
    design = policy.apply(design)
    design = allocator.allocate(design)
    validation = validator.validate(design)
    return {"design": design.model_dump(mode="json"), "validation": validation.model_dump()}
