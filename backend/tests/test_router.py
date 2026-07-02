"""Tests for provider routing and failover."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import Provider
from app.providers.router import provider_supports_request, route_generation
from app.providers.types import GenerationRequest, GenerationResult


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


@pytest.mark.asyncio
async def test_route_generation_failover(db_session):
    prov_a = Provider(
        name="FAL",
        display_name="fal.ai",
        model_name="fal-ai/test",
        priority=10,
        is_active=True,
        capabilities={"image_to_image": True},
    )
    prov_b = Provider(
        name="FAL_BACKUP",
        display_name="fal backup",
        model_name="fal-ai/backup",
        priority=20,
        is_active=True,
        capabilities={"image_to_image": True},
    )
    db_session.add_all([prov_a, prov_b])
    db_session.commit()

    request = GenerationRequest(
        workflow="CATALOG_IMAGE",
        prompt="test",
        image_urls=["/uploads/x.jpg"],
    )

    ok_result = GenerationResult(
        image_bytes=b"png",
        provider="FAL_BACKUP",
        model="fal-ai/backup",
        cost=0.1,
    )

    with patch("app.providers.router.get_active_providers", return_value=[prov_a, prov_b]):
        with patch("app.providers.router.build_adapter") as build:
            fail_adapter = AsyncMock()
            fail_adapter.generate = AsyncMock(side_effect=RuntimeError("primary down"))
            ok_adapter = AsyncMock()
            ok_adapter.generate = AsyncMock(return_value=ok_result)
            build.side_effect = [fail_adapter, ok_adapter]

            result, chain = await route_generation(db_session, request)

    assert result.provider == "FAL_BACKUP"
    assert chain == ["FAL", "FAL_BACKUP"]
