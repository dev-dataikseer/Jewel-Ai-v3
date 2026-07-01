import pytest

from app.pipeline.composer import slugify
from app.pipeline.layers import render_jinja
from app.providers.registry import filter_models_for_request
from seeds.fal_models_data import FAL_MODELS, WORKFLOW_DEFAULTS


def test_slugify():
    assert slugify("Ruby Red") == "ruby_red"


def test_jinja_render():
    text = render_jinja("Hello {{ jewelry_type }}", {"jewelry_type": "Ring"})
    assert text == "Hello Ring"


def test_fal_models_seed_catalog():
    assert len(FAL_MODELS) == 19
    ids = {m["endpoint_id"] for m in FAL_MODELS}
    assert "fal-ai/flux-pro/kontext" in ids
    assert "fal-ai/gpt-image-1.5/edit" in ids
    assert "fal-ai/ideogram/v3/remix" in ids
    assert "fal-ai/fashn/tryon/v1.6" in ids
    assert "fal-ai/kling/v1-5/kolors-virtual-try-on" in ids
    assert all("gemini" not in endpoint.lower() for endpoint in ids)


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


def test_recraft_has_prompt_limit():
    recraft = next(s for s in FAL_MODELS if s["endpoint_id"] == "fal-ai/recraft/v3/image-to-image")
    assert recraft["config"]["max_prompt_chars"] == 1000


def test_vton_models_restricted_to_try_on_workflows():
    vton = [s for s in FAL_MODELS if s.get("capabilities", {}).get("virtual_try_on")]
    assert len(vton) == 6
    for spec in vton:
        assert set(spec["workflow_allowlist"]) == {"JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"}


def test_workflow_defaults_point_to_seed():
    seed_ids = {m["endpoint_id"] for m in FAL_MODELS}
    for workflow, endpoint in WORKFLOW_DEFAULTS.items():
        assert endpoint.startswith("fal-ai/") or endpoint.startswith("bria/")
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
    assert len(models) == 13

    vton_models = filter_models_for_request(
        FakeDb(), has_input=True, image_count=2, workflow="CUSTOMER_TRY_ON", image_edit_only=True
    )
    assert len(vton_models) == 6

    class FakeDbWithT2I(FakeDb):
        def query(self, model):
            extra = FakeModel(
                {
                    "endpoint_id": "fal-ai/imagen4/preview",
                    "category": "text_to_image",
                    "capabilities": {"text_to_image": True, "image_to_image": False},
                    "config": {},
                    "sort_order": 999,
                }
            )
            return FakeQuery([FakeModel(s) for s in FAL_MODELS] + [extra])

    filtered = filter_models_for_request(
        FakeDbWithT2I(), has_input=True, image_count=1, image_edit_only=True
    )
    assert all(m.endpoint_id != "fal-ai/imagen4/preview" for m in filtered)


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
    assert len(models) == 13
