import pytest

from app.pipeline.composer import slugify
from app.pipeline.layers import render_jinja
from app.providers.registry import filter_models_for_request
from seeds.fal_models_data import FAL_MODELS, WORKFLOW_DEFAULTS

VALID_ENDPOINT_PREFIXES = ("fal-ai/", "bria/", "openai/", "ideogram/", "xai/", "decart/")


def test_slugify():
    assert slugify("Ruby Red") == "ruby_red"


def test_jinja_render():
    text = render_jinja("Hello {{ jewelry_type }}", {"jewelry_type": "Ring"})
    assert text == "Hello Ring"


def test_fal_models_seed_catalog():
    assert len(FAL_MODELS) == 25
    ids = {m["endpoint_id"] for m in FAL_MODELS}
    assert "fal-ai/gemini-3-pro-image-preview/edit" in ids
    assert "fal-ai/nano-banana-pro/edit" in ids
    assert "fal-ai/nano-banana/edit" in ids
    assert "fal-ai/nano-banana-2/edit" in ids
    assert "fal-ai/gemini-3.1-flash-image-preview/edit" in ids
    assert "fal-ai/flux-2-max/edit" in ids
    assert "openai/gpt-image-2/edit" in ids
    assert "fal-ai/glm-image/image-to-image" in ids
    assert "fal-ai/firered-image-edit-v1.1" in ids
    assert "fal-ai/gpt-image-1.5/edit" in ids
    assert "decart/lucy2-vton/realtime" in ids


def test_image_edit_models_ranked_nano_banana_first():
    image_edit = [m for m in FAL_MODELS if m["category"] == "image_to_image"]
    assert len(image_edit) == 18
    ranked = sorted(image_edit, key=lambda m: m["sort_order"])
    assert ranked[0]["endpoint_id"] == "fal-ai/nano-banana-pro/edit"
    assert ranked[1]["endpoint_id"] == "fal-ai/gemini-3-pro-image-preview/edit"
    assert ranked[2]["endpoint_id"] == "fal-ai/flux-2-max/edit"
    assert all(m["config"].get("model_info") for m in image_edit)
    assert WORKFLOW_DEFAULTS["CATALOG_IMAGE"] == "fal-ai/nano-banana-pro/edit"
    assert WORKFLOW_DEFAULTS["VIRTUAL_TRY_ON"] == "fal-ai/nano-banana-pro/edit"


def test_all_models_have_output_paths():
    for spec in FAL_MODELS:
        config = spec["config"]
        assert "output_paths" in config
        assert config["output_paths"]


def test_no_mask_required_models():
    for spec in FAL_MODELS:
        caps = spec["capabilities"]
        assert caps.get("requires_image") is True
        assert caps.get("requires_mask") is False
        assert caps.get("image_to_image") is True
        assert caps.get("text_to_image") is False
        config = spec["config"]
        if config.get("input_mode") != "try_on":
            assert config.get("image_field") in ("image_url", "image_urls")


def test_vton_models_restricted_to_try_on_workflows():
    vton = [s for s in FAL_MODELS if s.get("capabilities", {}).get("virtual_try_on")]
    assert len(vton) == 7
    for spec in vton:
        assert set(spec["workflow_allowlist"]) == {
            "VIRTUAL_TRY_ON",
            "JEWELRY_ON_MODEL",
            "CUSTOMER_TRY_ON",
        }


def test_workflow_defaults_point_to_seed():
    seed_ids = {m["endpoint_id"] for m in FAL_MODELS}
    for workflow, endpoint in WORKFLOW_DEFAULTS.items():
        assert endpoint.startswith(VALID_ENDPOINT_PREFIXES)
        assert endpoint in seed_ids, f"{workflow} default {endpoint} not in catalog"


def test_filter_models_image_edit_only():
    class FakeModel:
        def __init__(self, spec):
            self.endpoint_id = spec["endpoint_id"]
            self.category = spec["category"]
            self.capabilities = spec["capabilities"]
            self.workflow_allowlist = spec.get("workflow_allowlist")
            self.config = spec.get("config", {})
            self.is_active = True
            self.sort_order = spec.get("sort_order", 0)

    class FakeQuery:
        def __init__(self, models):
            self._models = models

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return self._models

    class FakeDb:
        def query(self, model):
            return FakeQuery([FakeModel(s) for s in FAL_MODELS])

    models = filter_models_for_request(FakeDb(), has_input=True, image_count=1, image_edit_only=True)
    vton_ids = {m.endpoint_id for m in models if m.capabilities.get("virtual_try_on")}
    assert len(vton_ids) == 0
    assert len(models) == 18

    vton_models = filter_models_for_request(
        FakeDb(), has_input=True, image_count=2, workflow="CUSTOMER_TRY_ON", image_edit_only=True
    )
    # I2I + VTON both available for jewelry try-on
    assert len(vton_models) >= 7
    assert any(m.capabilities.get("virtual_try_on") for m in vton_models)
    assert any(m.capabilities.get("image_to_image") and not m.capabilities.get("virtual_try_on") for m in vton_models)


def test_filter_without_input_still_lists_catalog_models():
    class FakeModel:
        def __init__(self, spec):
            self.endpoint_id = spec["endpoint_id"]
            self.capabilities = spec["capabilities"]
            self.workflow_allowlist = spec.get("workflow_allowlist")
            self.config = spec.get("config", {})
            self.is_active = True
            self.sort_order = spec.get("sort_order", 0)

    class FakeQuery:
        def __init__(self, models):
            self._models = models

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return self._models

    class FakeDb:
        def query(self, model):
            return FakeQuery([FakeModel(s) for s in FAL_MODELS])

    models = filter_models_for_request(FakeDb(), has_input=False, workflow="CATALOG_IMAGE")
    # flux-2-max is allowlisted away from catalog; expect remaining I2I
    assert len(models) == 17
