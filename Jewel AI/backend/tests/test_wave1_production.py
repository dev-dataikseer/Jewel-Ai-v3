"""Wave 1 regression tests: job claim, CDN host check, compose placeholders."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from app.providers.model_catalog.preprocess import _is_fal_cdn_url


def test_fal_cdn_url_rejects_substring_spoof():
    assert _is_fal_cdn_url("https://v3.fal.media/files/abc.png") is True
    assert _is_fal_cdn_url("https://fal.run/x") is True
    assert _is_fal_cdn_url("https://evil.example/?fal.ai") is False
    assert _is_fal_cdn_url("https://evilfal.ai/x") is False
    assert _is_fal_cdn_url("http://fal.media/x") is False


def test_process_job_skips_completed(monkeypatch):
    from app.tasks import job_runner as gen

    completed = SimpleNamespace(id="j1", status="COMPLETED", provider_metadata={})
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = completed

    monkeypatch.setattr(gen, "SessionLocal", lambda: db)

    import asyncio

    asyncio.run(gen._process_job_async("j1"))
    # Must not claim / force PROCESSING
    db.query.return_value.filter.return_value.update.assert_not_called()


def test_compose_catalog_master_file_with_placeholders(tmp_path, monkeypatch):
    """Imported V2 masters must compose without StrictUndefined crashes."""
    from app.pipeline.composer import ComposeInput, compose_prompt_document
    from app.pipeline.layer_derive import derive_layers_from_raw_text

    root = Path(__file__).resolve().parents[2] / "docs" / "Modals" / "Prompts"
    master_path = root / "CATALOG_IMAGE_master.txt"
    if not master_path.exists():
        import pytest
        pytest.skip("Prompt master file not found")
    text = master_path.read_text(encoding="utf-8")
    layers = derive_layers_from_raw_text(text, "CATALOG_IMAGE", scope="master")

    master_ver = SimpleNamespace(
        id="mv1",
        composition_mode="layered",
        raw_override=None,
        layers=layers,
        prompt_text=text,
        is_active=True,
    )
    master_tmpl = SimpleNamespace(id="mt1", is_active=True, active_version_id="mv1", workflow="CATALOG_IMAGE")

    subject_ver = SimpleNamespace(
        id="sv1",
        layers=[{"key": "core", "label": "Core", "order": 1, "type": "text", "content": "Ring shank rests flat.", "enabled": True}],
        prompt_text="Ring shank rests flat.",
        is_active=True,
        core_identity=None,
        material_accuracy=None,
        geometry_lock=None,
        placement_rules=None,
        lighting_reflection=None,
        scale_proportion=None,
        negative_constraints=None,
    )
    subject = SimpleNamespace(id="s1", is_active=True, active_version_id="sv1", workflow="CATALOG_IMAGE", jewelry_type="Ring")

    db = MagicMock()

    def _query(model):
        name = getattr(model, "__name__", str(model))
        q = MagicMock()
        if "PromptMasterTemplate" in name or "MasterTemplate" in name:
            q.filter.return_value.first.return_value = master_tmpl
        elif "PromptMasterVersion" in name or "MasterVersion" in name:
            q.filter.return_value.first.return_value = master_ver
            q.filter.return_value.order_by.return_value.first.return_value = master_ver
        elif "PromptSubjectVersion" in name:
            q.filter.return_value.first.return_value = subject_ver
            q.filter.return_value.order_by.return_value.first.return_value = subject_ver
        elif "PromptSubject" in name:
            q.filter.return_value.first.return_value = subject
        elif "PromptVariant" in name or "StylePreset" in name:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.order_by.return_value.first.return_value = None
        else:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.order_by.return_value.first.return_value = None
        return q

    db.query.side_effect = _query

    # Patch fragment lookups used by placeholder fills
    with patch("app.prompt_engine.fragment_store.get_fragment_text", return_value=""):
        with patch("app.pipeline.composer._get_active_master", return_value=(master_tmpl, master_ver)):
            with patch("app.pipeline.composer._get_active_subject", return_value=(subject, subject_ver)):
                with patch("app.pipeline.composer._get_active_variant", return_value=(None, None)):
                    with patch("app.pipeline.composer._resolve_master_layers", return_value=layers):
                        with patch(
                            "app.pipeline.composer._resolve_subject_layers",
                            return_value=subject_ver.layers,
                        ):
                            doc = compose_prompt_document(
                                db, ComposeInput(workflow="CATALOG_IMAGE", jewelry_type="Ring")
                            )
    assert doc.document.parts
    joined = " ".join(p.text for p in doc.document.parts)
    assert "{{" not in joined or "SUBTYPE" not in joined  # placeholders resolved or empty


def test_all_master_txt_files_compose_via_jinja_vars():
    from app.pipeline.layer_derive import derive_layers_from_raw_text
    from app.pipeline.layers import assemble_layer_parts
    from app.prompt_engine.fragment_defaults import PROMPT_PLACEHOLDERS

    root = Path(__file__).resolve().parents[2] / "docs" / "Modals" / "Prompts"
    for path in sorted(root.glob("*_master.txt")):
        wf = path.name.replace("_master.txt", "")
        text = path.read_text(encoding="utf-8")
        layers = derive_layers_from_raw_text(text, wf, scope="master")
        variables = {k: "" for k in PROMPT_PLACEHOLDERS}
        variables.update(
            {
                "workflow": wf,
                "jewelry_type": "Ring",
                "metal_type": "",
                "gemstone_type": "",
                "gemstone_target_color": "Emerald",
                "background_style": "",
                "lighting_style": "",
                "prompt_text": "soften highlights",
                "variant_text": "",
                "TARGET_COLOR": "Emerald",
                "USER_CUSTOM_INSTRUCTION": "soften highlights",
                "PLACEMENT_ANATOMY": "at the correct finger",
            }
        )
        body, neg, debug, parts = assemble_layer_parts(
            layers,
            [],
            composition_mode="layered",
            variables=variables,
        )
        assert parts is not None, path.name
