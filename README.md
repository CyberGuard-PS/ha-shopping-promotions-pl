# Shopping Promotions PL — Home Assistant

Custom integration for Home Assistant that enriches a shopping list with current
promotional offers for:

- Biedronka
- Lidl
- Auchan
- Rossmann
- Kaufland

The first data provider is **Blix.pl**, which exposes structured product data
inside current digital leaflets. The code is provider-based, so direct store
catalog/API adapters can be added later without changing the Home Assistant
entities.

## What the integration creates

1. **Enriched Todo list** (`todo.promocje_zakupowe` or a similar generated entity ID)
   - mirrors the selected source list, normally `todo.shopping_list`;
   - each item receives a description with matching stores, promotional price,
     regular price when available, validity dates, and the matched product name;
   - checking, renaming, adding or deleting an item in the enriched list is
     propagated to the source list.

2. **Sensor** (`sensor.produkty_na_promocji`)
   - state = number of shopping-list items for which at least one current offer
     was found;
   - attribute `items` contains the normalized matches and can be used in
     automations/templates.

3. Services/actions:
   - `shopping_promotions_pl.refresh`
   - `shopping_promotions_pl.clear_cache`

## Important limitation: availability vs. promotion

Blix is a promotional-leaflet source. A match means **"the product (or a close
name match) is present in a current promotional offer"**. A missing match does
**not** prove that the product is unavailable on a physical store shelf.

The Home Assistant native `shopping_list` entity also does not support the
Todo `description` field. For that reason this integration creates an enriched
mirror instead of modifying the original item names.

## Installation

### Manual

Copy:

```text
custom_components/shopping_promotions_pl/
```

to:

```text
/config/custom_components/shopping_promotions_pl/
```

Restart Home Assistant.

Then open:

```text
Settings -> Devices & services -> Add integration -> Shopping Promotions PL
```

### HACS custom repository

Put this project in a Git repository. In HACS add that repository as an
**Integration**, install it and restart Home Assistant.

## Configuration defaults

- source list: `todo.shopping_list`
- stores: all five supported stores
- network refresh: every 6 hours
- maximum current leaflet candidates: 8 per store
- fuzzy-match threshold: 0.58

The Blix adapter also uses a 3-hour in-memory cache so adding one product to the
shopping list does not immediately re-download all leaflet pages.

## Matching

The matcher:
- lowercases and removes Polish diacritics for comparison;
- removes common quantity/unit tokens;
- combines token containment, Jaccard similarity and edit-sequence similarity;
- deliberately gives a strong score to category-like shopping entries such as
  `mleko`, `masło`, `pasta do zębów`.

For precise matching, use names such as:

```text
Mleko Łaciate 3,2%
Persil żel 40 prań
Elmex Sensitive 75 ml
```

instead of only a broad category.

## Example description generated for an item

```text
Lidl: PROMOCJA 3,49 zł; cena regularna 4,99 zł; ważna 2026-09-17–2026-09-20; dopasowanie: Mleko UHT Łaciate 3,2%
Biedronka: PROMOCJA 3,79 zł; cena regularna brak danych; ważna 2026-09-18–2026-09-21; dopasowanie: Mleko UHT 3,2%
```

If the regular price is not explicitly present but Blix provides an unambiguous
percentage discount, the integration can derive it and marks that value with
`~`.

## Lovelace

Use the standard Home Assistant **To-do list card** and point it at the enriched
Todo entity created by this integration.

The summary sensor is also useful in a Tile/Entity card.

## Automations

Force a refresh:

```yaml
action: shopping_promotions_pl.refresh
```

Example notification when at least one item has a promotion:

```yaml
triggers:
  - trigger: state
    entity_id: sensor.produkty_na_promocji
conditions:
  - condition: numeric_state
    entity_id: sensor.produkty_na_promocji
    above: 0
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Promocje z listy zakupów"
      message: >
        Znaleziono promocje dla
        {{ states('sensor.produkty_na_promocji') }} pozycji.
```

## Data-source resilience

The integration is intentionally structured around `providers/`. The initial
release uses Blix as the common Polish promotion source. This avoids hard
dependency on undocumented mobile APIs and makes it possible to add:
- a direct Lidl Plus provider;
- Auchan online-catalog provider;
- Rossmann online-catalog provider;
- Biedronka application/catalog provider;
- Kaufland direct/catalog provider.

Direct catalogue providers are the next step if exact local-store stock or
non-promotional shelf prices are required.

## Upstream etiquette

Do not set aggressive refresh intervals. The default is intentionally low
frequency. The integration fetches only a limited number of leaflet pages and
caches results.


## v0.1.1

- Added Kaufland to supported and default monitored stores.
- Kaufland promotions are collected through the existing Blix provider (`/sklep/kaufland/`).
