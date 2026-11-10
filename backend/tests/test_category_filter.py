import unittest

from backend.services.rag_service import build_category_filters

class RagRegressionTests(unittest.TestCase):
    def test_build_category_filters_returns_none_for_empty_value(self):
        assert build_category_filters(None) is None
        assert build_category_filters("") is None
        assert build_category_filters("   ") is None


    def test_build_category_filters_matches_category_metadata(self):
        filters = build_category_filters("Tin học")

        assert filters is not None
        assert len(filters.filters) == 1
        assert filters.filters[0].key == "category"
        assert filters.filters[0].value == "Tin học"
