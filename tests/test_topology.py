from pathlib import Path

from app.services.allocator_service import AllocatorService
from app.services.design_builder_service import DesignBuilderService
from app.services.requirement_parser_service import RequirementParserService
from app.services.topology_service import TopologyService


def test_topology_has_nodes(tmp_path: Path):
    design = DesignBuilderService().build(RequirementParserService().parse("2 spines 4 leaf"))
    design = AllocatorService().allocate(design)
    dot, _, topo_json = TopologyService().render(design, tmp_path)
    assert "spine1" in dot
    assert "nodes" in topo_json
