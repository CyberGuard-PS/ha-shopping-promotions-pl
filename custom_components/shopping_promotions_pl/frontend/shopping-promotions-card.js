(() => {
  const CARD_TAG = "shopping-promotions-pl-card";
  const CARD_TYPE = "shopping-promotions-pl-card";

  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const money = (value) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "brak danych";
    }
    return `${Number(value).toFixed(2).replace(".", ",")} zł`;
  };

  const formatDate = (value) => {
    if (!value) return "brak danych";
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return String(value);
    return `${match[3]}.${match[2]}.${match[1]}`;
  };

  class ShoppingPromotionsPlCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._hass = undefined;
      this._config = {};
      this._busy = false;
      this._message = "";
    }

    static getStubConfig(hass) {
      const sensor = Object.entries(hass?.states || {}).find(
        ([entityId, state]) =>
          entityId.startsWith("sensor.") &&
          Array.isArray(state?.attributes?.items) &&
          state?.attributes?.source_entity_id
      );
      return sensor ? { entity: sensor[0], title: "Promocje zakupowe" } : {};
    }

    setConfig(config) {
      this._config = {
        title: "Promocje zakupowe",
        show_add: true,
        show_completed: true,
        ...config,
      };
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
      const count = this._getState()?.attributes?.items?.length || 1;
      return Math.max(3, Math.min(12, count * 2 + 2));
    }

    _resolveEntityId() {
      if (this._config?.entity && this._hass?.states?.[this._config.entity]) {
        return this._config.entity;
      }
      const sensor = Object.entries(this._hass?.states || {}).find(
        ([entityId, state]) =>
          entityId.startsWith("sensor.") &&
          Array.isArray(state?.attributes?.items) &&
          state?.attributes?.source_entity_id &&
          state?.attributes?.recommended_card === "custom:shopping-promotions-pl-card"
      );
      return sensor?.[0];
    }

    _getState() {
      const entityId = this._resolveEntityId();
      return entityId ? this._hass?.states?.[entityId] : undefined;
    }

    async _setCompleted(uid, completed) {
      const state = this._getState();
      const source = state?.attributes?.source_entity_id;
      if (!source || !uid || !this._hass) return;
      this._busy = true;
      this._message = "Aktualizowanie listy…";
      this._render();
      try {
        await this._hass.callService("todo", "update_item", {
          entity_id: source,
          item: uid,
          status: completed ? "completed" : "needs_action",
        });
        this._message = "";
      } catch (err) {
        this._message = `Nie udało się zaktualizować pozycji: ${err?.message || err}`;
      } finally {
        this._busy = false;
        this._render();
      }
    }

    async _addItem(value) {
      const state = this._getState();
      const source = state?.attributes?.source_entity_id;
      const item = String(value || "").trim();
      if (!source || !item || !this._hass) return;
      this._busy = true;
      this._message = "Dodawanie produktu…";
      this._render();
      try {
        await this._hass.callService("todo", "add_item", {
          entity_id: source,
          item,
        });
        this._message = "";
      } catch (err) {
        this._message = `Nie udało się dodać produktu: ${err?.message || err}`;
      } finally {
        this._busy = false;
        this._render();
      }
    }

    async _refreshPromotions() {
      if (!this._hass) return;
      this._busy = true;
      this._message = "Odświeżanie promocji…";
      this._render();
      try {
        await this._hass.callService("shopping_promotions_pl", "refresh", {});
        this._message = "Promocje odświeżone.";
      } catch (err) {
        this._message = `Nie udało się odświeżyć: ${err?.message || err}`;
      } finally {
        this._busy = false;
        this._render();
      }
    }

    _renderOffer(match, index, storeNames) {
      const store = storeNames?.[match.store] || match.store || "Sklep";
      const regular = match.regular_price_estimated
        ? `ok. ${money(match.regular_price)}`
        : money(match.regular_price);
      const discount =
        match.discount_percent !== null && match.discount_percent !== undefined
          ? `<span class="discount">−${escapeHtml(Math.round(Number(match.discount_percent)))}%</span>`
          : "";
      const sourceLink = match.source_url
        ? `<a class="source-link" href="${escapeHtml(match.source_url)}" target="_blank" rel="noopener noreferrer">Gazetka ↗</a>`
        : "";
      const cheapest = index === 0 ? `<span class="best">najniższa cena</span>` : "";

      return `
        <div class="offer">
          <div class="offer-top">
            <div class="store-line">
              <span class="store">${escapeHtml(store)}</span>
              ${cheapest}
            </div>
            <div class="price-line">
              <span class="promo-price">${escapeHtml(money(match.promo_price))}</span>
              ${discount}
            </div>
          </div>
          <div class="details-grid">
            <div><span class="label">Cena regularna</span><span class="value">${escapeHtml(regular)}</span></div>
            <div><span class="label">Promocja ważna</span><span class="value">${escapeHtml(formatDate(match.valid_from))} – ${escapeHtml(formatDate(match.valid_to))}</span></div>
            <div class="wide"><span class="label">Dopasowany produkt</span><span class="value">${escapeHtml(match.name || "brak danych")}</span></div>
            ${match.brand ? `<div><span class="label">Marka</span><span class="value">${escapeHtml(match.brand)}</span></div>` : ""}
            ${match.match_score !== null && match.match_score !== undefined ? `<div><span class="label">Pewność dopasowania</span><span class="value">${escapeHtml(Math.round(Number(match.match_score) * 100))}%</span></div>` : ""}
          </div>
          ${sourceLink}
        </div>
      `;
    }

    _renderItem(item, storeNames) {
      const completed = item.status === "completed";
      if (completed && this._config.show_completed === false) return "";
      const matches = Array.isArray(item.matches) ? item.matches : [];
      const countText = matches.length
        ? `${matches.length} ${matches.length === 1 ? "promocja" : matches.length < 5 ? "promocje" : "promocji"}`
        : "brak promocji";

      return `
        <section class="item ${completed ? "completed" : ""}">
          <div class="item-head">
            <input
              class="complete-checkbox"
              type="checkbox"
              data-uid="${escapeHtml(item.uid)}"
              ${completed ? "checked" : ""}
              ${this._busy ? "disabled" : ""}
              aria-label="Oznacz jako kupione"
            />
            <div class="item-title-wrap">
              <div class="item-title">${escapeHtml(item.summary || "Bez nazwy")}</div>
              <div class="item-meta ${matches.length ? "has-offer" : "no-offer"}">${escapeHtml(countText)}</div>
            </div>
          </div>
          ${
            matches.length
              ? `<div class="offers">${matches
                  .map((match, index) => this._renderOffer(match, index, storeNames))
                  .join("")}</div>`
              : `<div class="empty-offers">Nie znaleziono aktualnej promocji w wybranych sklepach. Nie oznacza to braku produktu na półce.</div>`
          }
        </section>
      `;
    }

    _render() {
      if (!this.shadowRoot) return;
      if (!this._hass) {
        this.shadowRoot.innerHTML = `<ha-card><div class="loading">Ładowanie…</div></ha-card>`;
        return;
      }

      const entityId = this._resolveEntityId();
      const state = this._getState();
      if (!state) {
        this.shadowRoot.innerHTML = `
          <ha-card>
            <div class="error">
              Nie znaleziono sensora Shopping Promotions PL.
              ${this._config?.entity ? `<br>Skonfigurowana encja: <code>${escapeHtml(this._config.entity)}</code>` : ""}
            </div>
          </ha-card>`;
        return;
      }

      const attrs = state.attributes || {};
      const items = Array.isArray(attrs.items) ? attrs.items : [];
      const visibleItems = this._config.show_completed === false
        ? items.filter((item) => item.status !== "completed")
        : items;
      const matched = items.filter((item) => Array.isArray(item.matches) && item.matches.length).length;
      const stores = Array.isArray(attrs.stores) ? attrs.stores.length : 0;
      const storeNames = attrs.store_names || {};

      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          ha-card { overflow: hidden; }
          .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 18px 20px 14px;
            border-bottom: 1px solid var(--divider-color);
          }
          .heading { min-width: 0; }
          .title {
            color: var(--primary-text-color);
            font-size: 20px;
            line-height: 1.3;
            font-weight: 500;
          }
          .subtitle {
            margin-top: 4px;
            color: var(--secondary-text-color);
            font-size: 13px;
            line-height: 1.4;
            white-space: normal;
          }
          button {
            font: inherit;
            color: var(--primary-text-color);
          }
          .refresh {
            flex: 0 0 auto;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            border-radius: 10px;
            padding: 8px 12px;
            cursor: pointer;
          }
          .refresh:hover { background: var(--secondary-background-color); }
          .refresh:disabled { opacity: .55; cursor: default; }
          .message {
            padding: 8px 20px;
            color: var(--secondary-text-color);
            background: var(--secondary-background-color);
            font-size: 13px;
            white-space: normal;
            overflow-wrap: anywhere;
          }
          .add-row {
            display: flex;
            gap: 8px;
            padding: 14px 20px;
            border-bottom: 1px solid var(--divider-color);
          }
          .add-row input[type="text"] {
            min-width: 0;
            flex: 1;
            box-sizing: border-box;
            border: 1px solid var(--divider-color);
            border-radius: 10px;
            padding: 10px 12px;
            color: var(--primary-text-color);
            background: var(--card-background-color);
            font: inherit;
          }
          .add-row button {
            border: 0;
            border-radius: 10px;
            padding: 10px 14px;
            background: var(--primary-color);
            color: var(--text-primary-color, white);
            cursor: pointer;
          }
          .list { padding: 0; }
          .item {
            padding: 16px 20px 18px;
            border-bottom: 1px solid var(--divider-color);
          }
          .item:last-child { border-bottom: 0; }
          .item.completed { opacity: .62; }
          .item-head {
            display: flex;
            align-items: flex-start;
            gap: 12px;
          }
          .complete-checkbox {
            width: 22px;
            height: 22px;
            margin: 2px 0 0;
            accent-color: var(--primary-color);
            flex: 0 0 auto;
          }
          .item-title-wrap { min-width: 0; flex: 1; }
          .item-title {
            color: var(--primary-text-color);
            font-size: 18px;
            line-height: 1.35;
            font-weight: 500;
            white-space: normal;
            overflow-wrap: anywhere;
          }
          .completed .item-title { text-decoration: line-through; }
          .item-meta {
            display: inline-block;
            margin-top: 6px;
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 12px;
            font-weight: 600;
          }
          .item-meta.has-offer {
            color: var(--success-color, #2e7d32);
            background: color-mix(in srgb, var(--success-color, #2e7d32) 14%, transparent);
          }
          .item-meta.no-offer {
            color: var(--secondary-text-color);
            background: var(--secondary-background-color);
          }
          .offers {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 290px), 1fr));
            gap: 10px;
            margin: 13px 0 0 34px;
          }
          .offer {
            min-width: 0;
            border: 1px solid var(--divider-color);
            border-radius: 12px;
            padding: 13px 14px;
            background: var(--secondary-background-color);
          }
          .offer-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
          }
          .store-line {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 6px;
            min-width: 0;
          }
          .store {
            color: var(--primary-text-color);
            font-size: 16px;
            font-weight: 700;
          }
          .best {
            border-radius: 999px;
            padding: 2px 7px;
            color: var(--primary-color);
            background: color-mix(in srgb, var(--primary-color) 13%, transparent);
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .02em;
          }
          .price-line {
            display: flex;
            align-items: center;
            gap: 6px;
            flex: 0 0 auto;
          }
          .promo-price {
            color: var(--primary-text-color);
            font-size: 19px;
            line-height: 1.1;
            font-weight: 700;
            white-space: nowrap;
          }
          .discount {
            border-radius: 6px;
            padding: 2px 5px;
            color: var(--error-color);
            background: color-mix(in srgb, var(--error-color) 12%, transparent);
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
          }
          .details-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px 14px;
          }
          .details-grid > div { min-width: 0; }
          .details-grid .wide { grid-column: 1 / -1; }
          .label,
          .value {
            display: block;
            white-space: normal;
            overflow-wrap: anywhere;
          }
          .label {
            color: var(--secondary-text-color);
            font-size: 11px;
            line-height: 1.3;
            text-transform: uppercase;
            letter-spacing: .03em;
          }
          .value {
            margin-top: 2px;
            color: var(--primary-text-color);
            font-size: 13px;
            line-height: 1.4;
          }
          .source-link {
            display: inline-block;
            margin-top: 11px;
            color: var(--primary-color);
            font-size: 12px;
            text-decoration: none;
          }
          .empty-offers {
            margin: 11px 0 0 34px;
            color: var(--secondary-text-color);
            font-size: 13px;
            line-height: 1.45;
            white-space: normal;
            overflow-wrap: anywhere;
          }
          .empty-list, .loading, .error {
            padding: 22px 20px;
            color: var(--secondary-text-color);
            line-height: 1.5;
            white-space: normal;
            overflow-wrap: anywhere;
          }
          code { color: var(--primary-text-color); }
          @media (max-width: 520px) {
            .header { align-items: flex-start; }
            .refresh { padding: 7px 9px; }
            .offers, .empty-offers { margin-left: 0; }
            .offer-top { flex-direction: column; gap: 8px; }
            .details-grid { grid-template-columns: 1fr; }
            .details-grid .wide { grid-column: auto; }
          }
        </style>
        <ha-card>
          <div class="header">
            <div class="heading">
              <div class="title">${escapeHtml(this._config.title || "Promocje zakupowe")}</div>
              <div class="subtitle">${matched} z ${items.length} produktów ma aktualną promocję · monitorowane sklepy: ${stores}</div>
            </div>
            <button class="refresh" type="button" ${this._busy ? "disabled" : ""}>↻ Odśwież</button>
          </div>
          ${this._message ? `<div class="message">${escapeHtml(this._message)}</div>` : ""}
          ${
            this._config.show_add === false
              ? ""
              : `<div class="add-row">
                   <input class="add-input" type="text" placeholder="Dodaj produkt do listy zakupów" ${this._busy ? "disabled" : ""} />
                   <button class="add-button" type="button" ${this._busy ? "disabled" : ""}>Dodaj</button>
                 </div>`
          }
          <div class="list">
            ${visibleItems.length
              ? visibleItems.map((item) => this._renderItem(item, storeNames)).join("")
              : `<div class="empty-list">Lista zakupów jest pusta.</div>`}
          </div>
          <div style="display:none" data-entity="${escapeHtml(entityId)}"></div>
        </ha-card>
      `;

      this.shadowRoot.querySelector(".refresh")?.addEventListener("click", () =>
        this._refreshPromotions()
      );

      this.shadowRoot.querySelectorAll(".complete-checkbox").forEach((checkbox) => {
        checkbox.addEventListener("change", (event) => {
          const target = event.currentTarget;
          this._setCompleted(target.dataset.uid, target.checked);
        });
      });

      const input = this.shadowRoot.querySelector(".add-input");
      const addButton = this.shadowRoot.querySelector(".add-button");
      const submit = () => {
        if (!input) return;
        const value = input.value;
        input.value = "";
        this._addItem(value);
      };
      addButton?.addEventListener("click", submit);
      input?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") submit();
      });
    }
  }

  if (!customElements.get(CARD_TAG)) {
    customElements.define(CARD_TAG, ShoppingPromotionsPlCard);
  }

  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
    window.customCards.push({
      type: CARD_TYPE,
      name: "Shopping Promotions PL",
      description: "Lista zakupów z pełnymi informacjami o promocjach bez skracania opisów.",
      preview: true,
    });
  }
})();
