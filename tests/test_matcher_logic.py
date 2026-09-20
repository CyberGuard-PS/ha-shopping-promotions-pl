"""Self-contained logic smoke tests."""
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).parents[1] / "custom_components" / "shopping_promotions_pl"

pkg = types.ModuleType("shopping_promotions_pl")
pkg.__path__ = [str(ROOT)]
sys.modules["shopping_promotions_pl"] = pkg

for name in ("models", "matcher"):
    spec = importlib.util.spec_from_file_location(
        f"shopping_promotions_pl.{name}", ROOT / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

matcher = sys.modules["shopping_promotions_pl.matcher"]
models = sys.modules["shopping_promotions_pl.models"]


def test_generic_product_matches_long_name():
    assert matcher.score("mleko", "Mleko UHT Łaciate 3,2% 1 l") >= 0.8


def test_unrelated_product_rejected():
    assert matcher.score("mleko", "Płyn do płukania Lenor") < 0.5


def test_best_per_store():
    offers = [
        models.Offer(store="lidl", name="Mleko UHT Łaciate 3,2%", promo_price=3.49),
        models.Offer(store="lidl", name="Mleko UHT inne", promo_price=3.19),
        models.Offer(store="biedronka", name="Mleko UHT 3,2%", promo_price=3.79),
    ]
    found = matcher.match_offers("mleko łaciate", offers, 0.45)
    assert any(x.store == "lidl" for x in found)
