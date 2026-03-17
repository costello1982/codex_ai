from app.services.requirement_parser_service import RequirementParserService


def test_parser_structure():
    text = "2 spines, 8 leaf switches, 2 border leafs, one pair in vpc, interconnect to another vxlan"
    intent = RequirementParserService().parse(text)
    assert intent.spine_count == 2
    assert intent.total_leaf_count == 8
    assert intent.vpc_pair_count == 1
    assert intent.interconnect_requested is True
