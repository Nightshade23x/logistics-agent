"""Tests for the get_hazard_class_info tool: service isolation + tool integration."""

from ..schemas.hazard_class import HazardClassInfoRequest
from ..services.hazard_class_service import HazardClassService
from .. import server


class FakeHazardClassRepository:
    """Fake repository implementing HazardClassRepository's interface for isolated tests."""

    def get_class_info(self, hazard_class: str):
        if hazard_class == "9":
            return {
                "name": "Miscellaneous Dangerous Substances and Articles",
                "description": "Test description.",
                "examples": ["Lithium batteries"],
            }
        return None


class TestHazardClassServiceIsolated:
    """Tests HazardClassService logic using a fake repository, no real data file."""

    def test_known_class_returns_full_details(self) -> None:
        service = HazardClassService(hazard_class_repository=FakeHazardClassRepository())
        response = service.get_info(HazardClassInfoRequest(hazard_class="9"))

        assert response.found is True
        assert response.name == "Miscellaneous Dangerous Substances and Articles"
        assert "Lithium batteries" in response.examples

    def test_unknown_class_returns_not_found(self) -> None:
        service = HazardClassService(hazard_class_repository=FakeHazardClassRepository())
        response = service.get_info(HazardClassInfoRequest(hazard_class="99"))

        assert response.found is False
        assert response.name is None
        assert response.examples == []


class TestGetHazardClassInfoToolIntegration:
    """Integration tests calling the server.py tool function directly with real data."""

    def test_class_9_returns_real_data(self) -> None:
        response = server.get_hazard_class_info(hazard_class="9")

        assert response.found is True
        assert response.name == "Miscellaneous Dangerous Substances and Articles"
        assert len(response.examples) > 0

    def test_unrecognized_class_returns_not_found(self) -> None:
        response = server.get_hazard_class_info(hazard_class="99")

        assert response.found is False