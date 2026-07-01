from dataclasses import dataclass
from enum import StrEnum


class JewelryCategory(StrEnum):
    RING = "Ring"
    NECKLACE = "Necklace"
    EARRINGS = "Earrings"
    BRACELET = "Bracelet"
    BROOCH = "Brooch"


class StrengthTier(StrEnum):
    HIGH_PRESERVATION = "HIGH_PRESERVATION"
    CONTROLLED_RECONTEXTUALIZATION = "CONTROLLED_RECONTEXTUALIZATION"
    CREATIVE_TRANSFORMATION = "CREATIVE_TRANSFORMATION"


@dataclass(frozen=True)
class JewelryGenerationIntent:
    workflow: str
    master_category: str
    child_category: str | None = None
    style: str | None = None
    model_endpoint_id: str | None = None
    strength: float = 0.3


def classify_strength_tier(strength: float) -> StrengthTier:
    if strength <= 0.3:
        return StrengthTier.HIGH_PRESERVATION
    if strength <= 0.6:
        return StrengthTier.CONTROLLED_RECONTEXTUALIZATION
    return StrengthTier.CREATIVE_TRANSFORMATION
