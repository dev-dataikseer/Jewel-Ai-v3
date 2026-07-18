"""Tests for canonical image packet assembly (product / theme / logo slots)."""

from types import SimpleNamespace

from app.pipeline.image_packet import build_image_packet
from app.prompt_engine.attachments import ImageContext, attachment_parts
from app.providers.model_catalog.spec import ImageContract, ModelSpec, ModelUiMeta


def _job(**kwargs):
    defaults = {
        "input_url": "https://cdn.example/product.png",
        "reference_url": None,
        "model_url": None,
        "workflow": "CATALOG_IMAGE",
        "provider_metadata": {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _spec(*, mode: str = "urls_array", max_images: int = 14, multi: bool = True) -> ModelSpec:
    return ModelSpec(
        endpoint_id="test/multi-edit",
        display_name="Test",
        family="nano_banana",
        category="edit",
        capabilities={"multi_image": multi},
        input_schema={},
        default_params={},
        image=ImageContract(
            mode=mode,  # type: ignore[arg-type]
            max_images=max_images,
            image_field="image_urls" if mode == "urls_array" else "image_url",
        ),
        ui=ModelUiMeta(provider="fal", provider_label="fal", tasks=("i2i",)),
    )


def test_packet_product_theme_logo_model_mode():
    job = _job(
        reference_url="https://cdn.example/theme.png",
        provider_metadata={"logoUrl": "https://cdn.example/logo.png"},
    )
    packet = build_image_packet(job, model_spec=_spec(max_images=14), force_compose=False)
    assert packet.logo_mode == "model"
    assert [r.role for r in packet.roles] == ["product", "theme", "logo"]
    assert len(packet.image_urls) == 3
    assert packet.has_logo is True
    meta = packet.to_meta()
    assert meta["logoMode"] == "model"
    assert len(meta["imageRoles"]) == 3


def test_packet_single_url_model_forces_compose_for_logo():
    job = _job(provider_metadata={"logoUrl": "https://cdn.example/logo.png"})
    packet = build_image_packet(
        job,
        model_spec=_spec(mode="single_url", max_images=1, multi=False),
        force_compose=False,
    )
    assert packet.logo_mode == "compose"
    assert [r.role for r in packet.roles] == ["product"]
    assert packet.has_logo is False


def test_packet_force_compose_flag():
    job = _job(
        reference_url="https://cdn.example/theme.png",
        provider_metadata={"logoUrl": "https://cdn.example/logo.png"},
    )
    packet = build_image_packet(job, model_spec=_spec(max_images=14), force_compose=True)
    assert packet.logo_mode == "compose"
    assert [r.role for r in packet.roles] == ["product", "theme"]


def test_packet_try_on_uses_portrait_not_theme():
    job = _job(
        workflow="CUSTOMER_TRY_ON",
        model_url="https://cdn.example/portrait.png",
        reference_url="https://cdn.example/ignored-theme.png",
        provider_metadata={"logoUrl": "https://cdn.example/logo.png"},
    )
    # max 2 → logo falls back to compose
    packet = build_image_packet(
        job,
        model_spec=_spec(mode="try_on_ordered", max_images=2),
        force_compose=False,
    )
    assert [r.role for r in packet.roles] == ["product", "portrait"]
    assert packet.logo_mode == "compose"


def test_packet_try_on_with_room_for_logo():
    job = _job(
        workflow="JEWELRY_ON_MODEL",
        model_url="https://cdn.example/portrait.png",
        provider_metadata={"logoUrl": "https://cdn.example/logo.png"},
    )
    packet = build_image_packet(
        job,
        model_spec=_spec(mode="urls_array", max_images=4),
        force_compose=False,
    )
    assert [r.role for r in packet.roles] == ["product", "portrait", "logo"]
    assert packet.logo_mode == "model"


def test_attachment_includes_logo_slot():
    parts = attachment_parts(
        "CATALOG_IMAGE",
        ImageContext(
            has_product=True,
            has_style_reference=True,
            has_logo=True,
            image_count=3,
            roles=[
                {"index": 1, "role": "product"},
                {"index": 2, "role": "theme"},
                {"index": 3, "role": "logo"},
            ],
        ),
    )
    keys = {p.key for p in parts}
    assert "attach_role_map" in keys
    role_map = next(p for p in parts if p.key == "attach_role_map")
    assert "Image 3" in role_map.text and "LOGO" in role_map.text.upper()
    assert "ENVIRONMENT REFERENCE" in role_map.text or "REFERENCE" in role_map.text.upper()


def test_packet_single_url_drops_theme_in_debug():
    job = _job(
        reference_url="https://cdn.example/theme.png",
        provider_metadata={"logoUrl": "https://cdn.example/logo.png"},
    )
    packet = build_image_packet(
        job,
        model_spec=_spec(mode="single_url", max_images=1, multi=False),
        force_compose=False,
    )
    assert [r.role for r in packet.roles] == ["product"]
    assert "theme" in (packet.debug.get("dropped_slots") or [])
    assert packet.logo_mode == "compose"


def test_validate_image_bytes_rejects_garbage():
    from app.providers.model_catalog.preprocess import detect_image_content_type, validate_image_bytes

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    assert detect_image_content_type(png) == "image/png"
    assert validate_image_bytes(png) == "image/png"
    try:
        validate_image_bytes(b"not-an-image" + b"\x00" * 64)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unsupported" in str(exc) or "corrupt" in str(exc)


def test_build_model_image_plan_warns_on_single_url_theme():
    from app.pipeline.image_prep import build_model_image_plan

    job = _job(
        reference_url="https://cdn.example/theme.png",
        provider_metadata={"logoUrl": "https://cdn.example/logo.png"},
    )
    plan = build_model_image_plan(job, model_spec=_spec(mode="single_url", max_images=1, multi=False))
    assert plan.contract_mode == "single_url"
    assert plan.field_map.get("field") == "image_url"
    assert any("Theme" in w or "theme" in w.lower() for w in plan.warnings)
