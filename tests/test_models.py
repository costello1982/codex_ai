from app.models.design_models import FabricDesign, SiteDesign


def test_fabric_requires_two_spines():
    try:
        FabricDesign(fabric_name="f", site=SiteDesign(site_name="s", site_id=1), spine_count=1, regular_leaf_count=1, border_leaf_count=0)
        assert False
    except ValueError:
        assert True
