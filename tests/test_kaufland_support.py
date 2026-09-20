from pathlib import Path


def test_kaufland_is_supported_and_default():
    const = (
        Path(__file__).parents[1]
        / "custom_components"
        / "shopping_promotions_pl"
        / "const.py"
    ).read_text(encoding="utf-8")
    assert '"kaufland"' in const
    assert '"kaufland": "Kaufland"' in const
