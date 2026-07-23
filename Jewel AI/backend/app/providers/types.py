from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import ModelDefinition


@dataclass
class ModelCapabilities:
    text_to_image: bool = True
    image_to_image: bool = True
    inpainting: bool = False
    person_generation: bool = False
    material_accuracy: bool = True
    max_resolution: str = "1024x1024"


@dataclass
class GenerationRequest:
    prompt: str
    negative_prompt: str = ""
    image_urls: list[str] = field(default_factory=list)
    aspect_ratio: str = "1:1"
    workflow: str = "CATALOG_IMAGE"
    model_override: str | None = None
    model_endpoint_id: str | None = None
    model_params: dict[str, Any] = field(default_factory=dict)
    person_generation: str = "ALLOW_ADULT"
    number_of_images: int = 1
    job_id: str | None = None


@dataclass
class GenerationResult:
    image_bytes: bytes | None
    provider: str
    model: str
    cost: float = 0.0
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    is_webhook_pending: bool = False


@dataclass
class ProviderStatus:
    healthy: bool
    message: str = ""
    latency_ms: float | None = None


@runtime_checkable
class ProviderAdapter(Protocol):
    """Abstraction that all provider adapters must satisfy.

    High-level modules (router, registry) depend on this protocol rather
    than concrete adapter classes, satisfying the Dependency Inversion
    Principle. Adding a new provider only requires implementing this protocol.
    """

    async def generate(
        self,
        request: GenerationRequest,
        *,
        model_def: ModelDefinition | None = None,
        db: Session | None = None,
    ) -> GenerationResult:
        """Run image generation and return a result."""
        ...

    async def health_check(self) -> ProviderStatus:
        """Return the current health of this provider."""
        ...

