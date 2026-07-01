from app.models import Provider
from app.providers.router import provider_supports_request
from app.providers.types import GenerationRequest


def test_capability_gating_person_generation():
    prov = Provider(
        name="FAL",
        display_name="fal.ai",
        model_name="fal-ai/flux-pro/kontext",
        priority=10,
        is_active=True,
        capabilities={"text_to_image": False, "image_to_image": True, "person_generation": False},
    )
    req = GenerationRequest(workflow="JEWELRY_ON_MODEL", prompt="test", image_urls=["/uploads/x.jpg"])
    assert provider_supports_request(prov, req) is False


def test_capability_gating_image_required():
    prov = Provider(
        name="FAL",
        display_name="fal.ai",
        model_name="fal-ai/flux-pro/kontext",
        priority=10,
        is_active=True,
        capabilities={"text_to_image": False, "image_to_image": True},
    )
    req = GenerationRequest(workflow="CATALOG_IMAGE", prompt="test", image_urls=["/uploads/x.jpg"])
    assert provider_supports_request(prov, req) is True

    req2 = GenerationRequest(workflow="CATALOG_IMAGE", prompt="test", image_urls=[])
    assert provider_supports_request(prov, req2) is False
