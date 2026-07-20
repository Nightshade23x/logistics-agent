"""Service responsible for looking up IMDG hazard class reference info."""

from ..repositories.hazard_class_repository import HazardClassRepository
from ..schemas.hazard_class import HazardClassInfoRequest, HazardClassInfoResponse


class HazardClassService:
    """Looks up reference details for a given IMDG hazard class number."""

    def __init__(self, hazard_class_repository: HazardClassRepository) -> None:
        """Initialize the HazardClassService with its repository dependency.

        Args:
            hazard_class_repository: Provides IMDG hazard class reference data.
        """
        self._hazard_class_repository = hazard_class_repository

    def get_info(self, request: HazardClassInfoRequest) -> HazardClassInfoResponse:
        """Look up name/description/examples for a hazard class number.

        Args:
            request: The validated hazard class info request.

        Returns:
            A HazardClassInfoResponse with the class details, or found=False
            if the hazard class number is not recognized.
        """
        normalized_class = request.hazard_class.strip()
        class_info = self._hazard_class_repository.get_class_info(normalized_class)

        if class_info is None:
            return HazardClassInfoResponse(
                hazard_class=request.hazard_class,
                found=False,
                name=None,
                description=None,
                examples=[],
            )

        return HazardClassInfoResponse(
            hazard_class=request.hazard_class,
            found=True,
            name=class_info["name"],
            description=class_info["description"],
            examples=class_info.get("examples", []),
        )