# Shopping Promotions PL — Home Assistant

Custom integration for Home Assistant that enriches a shopping list with current
promotional offers for:

- Biedronka
- Lidl
- Auchan
- Rossmann
- Kaufland

The current common data provider is **Blix.pl**. The provider layer is separated
from Home Assistant entities so direct store APIs/catalogues can be added later.

## v0.2.0 — full promotion view and configurable options

Version 0.2.0 adds two important features:

1. **Options Flow** — after installation open:

   `Settings -> Devices & services -> Shopping Promotions PL -> Configure`

   You can change the source Todo list, monitored stores, update interval,
   maximum leaflet count and product matching threshold without deleting and
   re-adding the integration.

2. **Bundled dashboard card** — `custom:shopping-promotions-pl-card`.

   Home Assistant's built-in To-do list UI can visually shorten long descriptions
   with `...`. The integration cannot change the CSS of Home Assistant's core
   To-do panel, so v0.2.0 includes its own card which displays the **complete
   promotion information without ellipsis**.

The JavaScript card is served and loaded automatically by the integration. No
manual Lovelace resource entry is required.

## What the integration creates

### 1. Enriched Todo list

Usually:

```text
todo.promocje_zakupowe
```

It mirrors the selected source list (normally `todo.shopping_list`). Checking,
renaming, adding or deleting an item is propagated to the source list.

The native Todo description was also reformatted in v0.2.0. Its first line is a
compact price summary, followed by Markdown sections for individual stores, for
example:

```text
Lidl: 2,19 zł • Biedronka: 3,49 zł

Lidl — PROMOCJA 2,19 zł
Cena regularna: brak danych
Ważna: 21.08.2026 – 30.09.2026
Dopasowanie: Mleko UHT Pilos 0,5%
```

The core Home Assistant To-do frontend may still visually clamp this description.
Use the bundled card below when you want all information visible directly on the
dashboard.

### 2. Promotion summary sensor

Usually:

```text
sensor.produkty_na_promocji
```

Its state is the number of shopping-list items for which at least one current
promotion was found. Its attributes contain the full normalized result set,
including:

- source Todo entity;
- selected stores;
- product name;
- matched product name;
- promotional price;
- regular price when available;
- whether regular price was estimated;
- discount percentage when available;
- validity dates;
- match confidence;
- Blix leaflet URL.

### 3. Dedicated Shopping Promotions card

Add a card to a dashboard using:

```yaml
type: custom:shopping-promotions-pl-card
entity: sensor.produkty_na_promocji
title: Promocje zakupowe
```

In most installations `entity` can be omitted because the card auto-detects the
Shopping Promotions PL sensor:

```yaml
type: custom:shopping-promotions-pl-card
title: Promocje zakupowe
```

The card displays each shopping-list product separately. Every matching store is
shown in its own panel with:

- store name;
- promotional price;
- regular price;
- discount percentage when available;
- promotion start and end date;
- exact product name matched in the leaflet;
- matching confidence;
- link to the source leaflet.

Long text wraps normally; it is **not** rendered with `text-overflow: ellipsis`.
The card also lets you:

- mark an item as bought/unbought;
- add a new item to the source shopping list;
- force-refresh promotion data.

Optional card settings:

```yaml
type: custom:shopping-promotions-pl-card
entity: sensor.produkty_na_promocji
title: Zakupy
show_add: true
show_completed: true
```

Set `show_completed: false` if completed shopping-list positions should disappear
from the card.

### 4. Services/actions

```yaml
action: shopping_promotions_pl.refresh
```

and:

```yaml
action: shopping_promotions_pl.clear_cache
```

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

Restart Home Assistant and then open:

```text
Settings -> Devices & services -> Add integration -> Shopping Promotions PL
```

Because v0.2.0 contains a frontend JavaScript module, after an upgrade it is a
good idea to perform a hard refresh of the browser/app frontend after restarting
Home Assistant.

### HACS custom repository

Add the GitHub repository to HACS as an **Integration**, install it and restart
Home Assistant.

## Upgrading from v0.1.1

Replace the old `custom_components/shopping_promotions_pl/` directory with the
v0.2.0 directory, restart Home Assistant and hard-refresh the browser.

Your existing Config Entry remains valid. New configuration changes can then be
made through **Configure** because v0.2.0 reads Options Flow values with priority
over the original installation data.

## Configuration defaults

- source list: `todo.shopping_list`
- stores: Biedronka, Lidl, Auchan, Rossmann, Kaufland
- network refresh: every 6 hours
- maximum current leaflet candidates: 8 per store
- fuzzy-match threshold: 0.58

The Blix adapter uses a 3-hour in-memory cache to avoid repeatedly downloading
leaflet pages when the shopping list changes.

## Matching

The matcher:

- lowercases and removes Polish diacritics for comparison;
- removes common quantity/unit tokens;
- combines token containment, Jaccard similarity and edit-sequence similarity;
- gives a strong score to category-like entries such as `mleko`, `masło` or
  `pasta do zębów`.

For more precise results use names such as:

```text
Mleko Łaciate 3,2%
Persil żel 40 prań
Elmex Sensitive 75 ml
```

instead of only a broad category.

## Important limitation: availability vs. promotion

Blix is a promotional-leaflet source. A match means **the product (or a close
name match) is present in a currently valid promotional offer**. A missing match
does not prove that a product is unavailable on a physical store shelf.

Likewise, Blix does not always expose the regular shelf price. If an unambiguous
discount percentage is available, the integration can calculate an estimated
regular price and marks it as `ok.`. Otherwise it reports `brak danych` instead
of inventing a price.

## Data-source architecture

The integration is structured around `providers/`. The current release uses
Blix as a common promotion source. The architecture allows future direct
providers for:

- Lidl Plus;
- Auchan online catalogue;
- Rossmann online catalogue;
- Biedronka application/catalogue;
- Kaufland catalogue.

Direct catalogue providers are required if exact local-store stock or reliable
non-promotional shelf prices are needed.

## Changelog

### v0.2.0

- Added **Options Flow** with automatic integration reload.
- Added bundled `custom:shopping-promotions-pl-card`.
- Card shows complete promotion data without description truncation.
- Added add-item, checkbox synchronization and manual refresh to the card.
- Improved native Todo Markdown descriptions and Polish date formatting.
- Added sensor metadata required by the card.

### v0.1.1

- Added Kaufland to supported and default monitored stores.
