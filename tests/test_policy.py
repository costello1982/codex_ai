import pytest

from app.services.design_builder_service import DesignBuilderService
from app.services.policy_engine_service import PolicyEngineService
from app.services.requirement_parser_service import RequirementParserService


def test_policy_interconnect_requires_border_leaf():
    intent = RequirementParserService().parse("2 spines 4 leaf interconnect to another vxlan")
    intent.border_leaf_count = 0
    design = DesignBuilderService().build(intent)
    with pytest.raises(ValueError):
        PolicyEngineService().apply(design)
