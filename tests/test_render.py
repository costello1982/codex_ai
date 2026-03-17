from app.services.allocator_service import AllocatorService
from app.services.config_renderer_service import ConfigRendererService
from app.services.design_builder_service import DesignBuilderService
from app.services.requirement_parser_service import RequirementParserService


def test_template_rendering_contains_hostname():
    design = DesignBuilderService().build(RequirementParserService().parse("2 spines 4 leaf"))
    design = AllocatorService().allocate(design)
    configs = ConfigRendererService().render(design)
    sample = next(iter(configs.values()))
    assert "hostname" in sample
