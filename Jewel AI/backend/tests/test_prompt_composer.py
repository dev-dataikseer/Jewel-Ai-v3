"""Golden tests for DB-driven layer assembler."""

import copy

from app.pipeline.layers import assemble_layers, default_master_scaffold, sort_layers


def _sample_master():
    layers = default_master_scaffold()
    layers.extend(
        [
            {
                "key": "system_role",
                "label": "System role",
                "order": 2,
                "content": "Act as a jewelry photographer for {{ jewelry_type }}.",
                "locked": False,
                "type": "text",
            },
            {
                "key": "negative_prompt",
                "label": "Negative",
                "order": 99,
                "content": "CGI, watermark",
                "locked": False,
                "type": "negative",
            },
        ]
    )
    return layers


def _sample_subject():
    return [
        {
            "key": "core_description",
            "label": "Core",
            "order": 1,
            "content": "A luxury {{ jewelry_type }} on velvet.",
            "locked": False,
            "type": "text",
        },
    ]


def test_generic_extra_layer_appears_without_code_change():
    master = _sample_master()
    master.append(
        {
            "key": "extra_scene",
            "label": "Extra",
            "order": 50,
            "content": "UNIQUE_LAYER_MARKER",
            "locked": False,
            "type": "text",
        }
    )
    body, _, _ = assemble_layers(master, _sample_subject(), variables={"jewelry_type": "Bracelet"})
    assert "UNIQUE_LAYER_MARKER" in body


def test_raw_mode_uses_override_only():
    master = _sample_master()
    body, _, debug = assemble_layers(
        master,
        _sample_subject(),
        composition_mode="raw",
        raw_override="Custom scene for {{ jewelry_type }}.",
        variables={"jewelry_type": "Bracelet"},
    )
    assert "Custom scene for Bracelet." in body
    assert debug["mode"] == "raw"


def test_raw_mode_separates_negative():
    master = _sample_master()
    _, negative, _ = assemble_layers(
        master,
        _sample_subject(),
        composition_mode="raw",
        raw_override="Scene only.",
        variables={"jewelry_type": "Bracelet"},
    )
    assert "CGI" in negative


def test_subject_insert_renders_child_layers():
    body, _, _ = assemble_layers(_sample_master(), _sample_subject(), variables={"jewelry_type": "Bracelet"})
    assert "Bracelet" in body
    assert "velvet" in body.lower()


def test_layer_order_respected_after_reorder():
    master = copy.deepcopy(_sample_master())
    reordered = sort_layers(master)
    role = next(l for l in reordered if l["key"] == "system_role")
    subject_marker = next(l for l in reordered if l["key"] == "subject_insert")
    role["order"] = 1
    subject_marker["order"] = 10
    baseline = copy.deepcopy(_sample_master())
    body_a, _, _ = assemble_layers(reordered, _sample_subject(), variables={"jewelry_type": "Ring"})
    body_b, _, _ = assemble_layers(baseline, _sample_subject(), variables={"jewelry_type": "Ring"})
    assert body_a != body_b
    assert body_a.index("jewelry photographer") < body_a.index("velvet")
    assert body_b.index("velvet") < body_b.index("jewelry photographer")


def test_user_instruction_appended():
    body, _, _ = assemble_layers(
        _sample_master(),
        _sample_subject(),
        user_instruction="Add soft sparkles",
        variables={"jewelry_type": "Ring"},
    )
    assert "User addition (must not override preservation): Add soft sparkles" in body


def test_empty_subject_layers_ok():
    body, _, _ = assemble_layers(_sample_master(), [], variables={"jewelry_type": "Ring"})
    assert "jewelry photographer" in body.lower()


def test_disabled_layers_skipped():
    master = copy.deepcopy(_sample_master())
    for layer in master:
        if layer["key"] == "system_role":
            layer["enabled"] = False
    body, _, debug = assemble_layers(master, _sample_subject(), variables={"jewelry_type": "Ring"})
    assert "jewelry photographer" not in body.lower()
    assert any(d.get("included") == "disabled" for d in debug["layers"])


def test_multi_subject_insert_renders_each_type():
    ring_subject = [
        {
            "key": "core_description",
            "label": "Core",
            "order": 1,
            "content": "A luxury {{ jewelry_type }} on velvet.",
            "locked": False,
            "type": "text",
        },
    ]
    necklace_subject = [
        {
            "key": "core_description",
            "label": "Core",
            "order": 1,
            "content": "Elegant {{ jewelry_type }} draped on bust.",
            "locked": False,
            "type": "text",
        },
    ]
    body, _, debug = assemble_layers(
        _sample_master(),
        [],
        subject_layers_by_type=[("Ring", ring_subject), ("Necklace", necklace_subject)],
        variables={"jewelry_type": "Ring, Necklace"},
    )
    assert "luxury Ring on velvet" in body
    assert "Elegant Necklace draped" in body
    assert "distinct jewelry items" in body
    assert debug["layers"][0]["parts"] == 4


def test_parse_and_normalize_jewelry_types():
    from app.pipeline.validator import normalize_jewelry_types, parse_jewelry_types

    assert parse_jewelry_types("Ring, Necklace") == ["Ring", "Necklace"]
    assert parse_jewelry_types("Ring, Ring, Necklace") == ["Ring", "Necklace"]
    assert parse_jewelry_types(None) == ["Ring"]
    assert normalize_jewelry_types(["Ring", "Multiple Items", "Necklace"]) == ["Ring", "Necklace"]
    assert normalize_jewelry_types(["Multiple Items"]) == ["Multiple Items"]
