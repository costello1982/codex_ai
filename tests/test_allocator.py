from app.services.allocator_service import AllocatorService
from app.services.design_builder_service import DesignBuilderService
from app.services.requirement_parser_service import RequirementParserService


def test_unique_loopbacks():
    intent = RequirementParserService().parse("2 spines 6 leaf 2 border leaf one pair vpc")
    design = DesignBuilderService().build(intent)
    design = AllocatorService().allocate(design)
    loops = [d.loopback0 for d in design.devices]
    assert len(loops) == len(set(loops))
