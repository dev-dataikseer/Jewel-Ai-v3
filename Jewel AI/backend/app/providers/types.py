from dataclasses import dataclass, field
from typing import Any


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
