"""Static smoke tests for v0.2.0 UI/options additions."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "shopping_promotions_pl"


def test_manifest_version_and_frontend_dependency():
    manifest = (COMPONENT / "manifest.json").read_text(encoding="utf-8")
    assert '"version": "0.2.0"' in manifest
    assert '"frontend"' in manifest


def test_options_flow_is_present():
    config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    assert "async_get_options_flow" in config_flow
    assert "ShoppingPromotionsOptionsFlow" in config_flow


def test_custom_card_is_bundled_and_does_not_clamp_text():
    card = (
        COMPONENT / "frontend" / "shopping-promotions-card.js"
    ).read_text(encoding="utf-8")
    assert "shopping-promotions-pl-card" in card
    assert "overflow-wrap: anywhere" in card
    assert "text-overflow: ellipsis" not in card
    assert "Dopasowany produkt" in card


def test_native_description_uses_multiline_markdown():
    todo = (COMPONENT / "todo.py").read_text(encoding="utf-8")
    assert "Cena regularna:" in todo
    assert "Ważna:" in todo
    assert "Dopasowanie:" in todo
    assert '"\\n\\n".join(sections)' in todo
