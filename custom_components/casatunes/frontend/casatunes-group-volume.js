const FEATURE_TYPE = "casatunes-group-volume-card-feature";

const ICONS = Object.freeze({
  close: `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4-6.3-6.3-6.3 6.3-1.4-1.4L9.2 12 2.9 5.7l1.4-1.4 6.3 6.3 6.3-6.3z"/>
    </svg>`,
  group: `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 3.2v17.6c0 .7-.8 1.1-1.4.7L7.3 17H4a2 2 0 0 1-2-2V9c0-1.1.9-2 2-2h3.3l5.3-4.5c.6-.4 1.4 0 1.4.7Zm3.2 3.1a1 1 0 0 1 1.4 0 8 8 0 0 1 0 11.4 1 1 0 1 1-1.4-1.4 6 6 0 0 0 0-8.6 1 1 0 0 1 0-1.4Zm2.9-2.8a1 1 0 0 1 1.4 0 12 12 0 0 1 0 17 1 1 0 0 1-1.4-1.4 10 10 0 0 0 0-14.2 1 1 0 0 1 0-1.4Z"/>
    </svg>`,
  minus: `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 11h14v2H5z"/>
    </svg>`,
  muted: `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m16.5 12 2.2 2.2-1.4 1.4-2.2-2.2-2.2 2.2-1.4-1.4 2.2-2.2-2.2-2.2 1.4-1.4 2.2 2.2 2.2-2.2 1.4 1.4zM4 9h3l4-3.4v12.8L7 15H4a2 2 0 0 1-2-2v-2c0-1.1.9-2 2-2Z"/>
    </svg>`,
  plus: `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z"/>
    </svg>`,
  volume: `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 9h3l5-4.2v14.4L7 15H4a2 2 0 0 1-2-2v-2c0-1.1.9-2 2-2Zm11.6-1.6a1 1 0 0 1 1.4 0 6.5 6.5 0 0 1 0 9.2 1 1 0 1 1-1.4-1.4 4.5 4.5 0 0 0 0-6.4 1 1 0 0 1 0-1.4Zm2.8-2.8a1 1 0 0 1 1.4 0 10.5 10.5 0 0 1 0 14.8 1 1 0 0 1-1.4-1.4 8.5 8.5 0 0 0 0-12 1 1 0 0 1 0-1.4Z"/>
    </svg>`,
});

const escapeHtml = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
      })[character],
  );

const clampVolume = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.min(1, Math.max(0, parsed)) : 0;
};

class CasaTunesGroupVolumeCardFeature extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._context = {};
    this._dialogOpen = false;
    this.shadowRoot.addEventListener("click", (event) => this._handleClick(event));
    this.shadowRoot.addEventListener("input", (event) => this._handleInput(event));
    this.shadowRoot.addEventListener("change", (event) => this._handleChange(event));
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set context(context) {
    this._context = context || {};
    this._render();
  }

  get context() {
    return this._context;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  _entityId() {
    return this._config.entity || this._context.entity_id;
  }

  _state(entityId) {
    return this._hass?.states?.[entityId];
  }

  _name(entityId) {
    const state = this._state(entityId);
    return state?.attributes?.friendly_name || entityId;
  }

  _slaveIds(masterState) {
    const members = Array.isArray(masterState?.attributes?.group_members)
      ? masterState.attributes.group_members
      : [];
    return [...new Set(members)].filter((entityId) => {
      const state = this._state(entityId);
      return (
        entityId !== masterState.entity_id &&
        state &&
        state.state !== "unavailable" &&
        state.state !== "unknown"
      );
    });
  }

  _volumeControl(entityId, role) {
    const state = this._state(entityId);
    if (!state) return "";
    const volume = clampVolume(state.attributes.volume_level);
    const percentage = Math.round(volume * 100);
    const muted = Boolean(state.attributes.is_volume_muted);
    const disabled = state.state === "unavailable";
    return `
      <div class="room ${role}">
        <div class="room-heading">
          <div>
            ${role === "master" ? '<span class="role-label">Master</span>' : ""}
            <div class="room-name">${escapeHtml(this._name(entityId))}</div>
          </div>
          <span class="volume-value" data-value-for="${escapeHtml(entityId)}">${percentage}%</span>
        </div>
        <div class="room-controls">
          <button
            class="icon-button"
            data-action="volume-down"
            data-entity="${escapeHtml(entityId)}"
            aria-label="Volume down for ${escapeHtml(this._name(entityId))}"
            title="Volume down"
            ${disabled ? "disabled" : ""}
          >${ICONS.minus}</button>
          <input
            class="volume-slider"
            data-volume-entity="${escapeHtml(entityId)}"
            type="range"
            min="0"
            max="1"
            step="0.01"
            value="${volume}"
            style="--volume-percent: ${percentage}%"
            aria-label="Volume for ${escapeHtml(this._name(entityId))}"
            ${disabled ? "disabled" : ""}
          />
          <button
            class="icon-button"
            data-action="volume-up"
            data-entity="${escapeHtml(entityId)}"
            aria-label="Volume up for ${escapeHtml(this._name(entityId))}"
            title="Volume up"
            ${disabled ? "disabled" : ""}
          >${ICONS.plus}</button>
          <button
            class="icon-button ${muted ? "active" : ""}"
            data-action="mute"
            data-entity="${escapeHtml(entityId)}"
            aria-label="${muted ? "Unmute" : "Mute"} ${escapeHtml(this._name(entityId))}"
            aria-pressed="${muted}"
            title="${muted ? "Unmute" : "Mute"}"
            ${disabled ? "disabled" : ""}
          >${muted ? ICONS.muted : ICONS.volume}</button>
        </div>
      </div>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const entityId = this._entityId();
    const master = this._state(entityId);
    if (!entityId || !master) {
      this.shadowRoot.innerHTML = `
        <style>${this._styles()}</style>
        <div class="message">CasaTunes media player not found.</div>`;
      return;
    }

    const slaveIds = this._slaveIds(master);
    const volume = clampVolume(master.attributes.volume_level);
    const percentage = Math.round(volume * 100);
    const muted = Boolean(master.attributes.is_volume_muted);
    const unavailable = master.state === "unavailable";
    const groupLabel = slaveIds.length
      ? `Group volume, ${slaveIds.length + 1} rooms`
      : "No grouped rooms";

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <div class="feature-row">
        <button
          class="feature-button ${muted ? "active" : ""}"
          data-action="mute"
          data-entity="${escapeHtml(entityId)}"
          aria-label="${muted ? "Unmute" : "Mute"} ${escapeHtml(this._name(entityId))}"
          aria-pressed="${muted}"
          title="${muted ? "Unmute" : "Mute"}"
          ${unavailable ? "disabled" : ""}
        >${muted ? ICONS.muted : ICONS.volume}</button>
        <input
          class="volume-slider main-slider"
          data-volume-entity="${escapeHtml(entityId)}"
          type="range"
          min="0"
          max="1"
          step="0.01"
          value="${volume}"
          style="--volume-percent: ${percentage}%"
          aria-label="Volume for ${escapeHtml(this._name(entityId))}"
          ${unavailable ? "disabled" : ""}
        />
        <button
          class="feature-button group-button"
          data-action="open-group"
          aria-label="${groupLabel}"
          title="${groupLabel}"
          ${slaveIds.length ? "" : "disabled"}
        >
          ${ICONS.group}
          ${slaveIds.length ? `<span class="count">${slaveIds.length + 1}</span>` : ""}
        </button>
      </div>
      <dialog aria-labelledby="casatunes-group-title">
        <div class="dialog-shell">
          <header>
            <div>
              <h2 id="casatunes-group-title">Grouped speakers</h2>
              <p>${slaveIds.length + 1} active rooms</p>
            </div>
            <button class="close-button" data-action="close" aria-label="Close">
              ${ICONS.close}
            </button>
          </header>
          ${this._volumeControl(entityId, "master")}
          <div class="slave-heading">Joined rooms</div>
          <div class="slave-list">
            ${slaveIds.map((slaveId) => this._volumeControl(slaveId, "slave")).join("")}
          </div>
        </div>
      </dialog>`;

    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog) {
      dialog.addEventListener("cancel", () => {
        this._dialogOpen = false;
      });
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) this._closeDialog();
      });
    }
    if (this._dialogOpen && slaveIds.length) {
      queueMicrotask(() => {
        if (dialog && !dialog.open) dialog.showModal();
      });
    } else if (!slaveIds.length) {
      this._dialogOpen = false;
    }
  }

  _styles() {
    return `
      :host {
        display: block;
        color: var(--primary-text-color);
        font-family: var(--ha-font-family-body, inherit);
      }
      * { box-sizing: border-box; }
      svg { width: 22px; height: 22px; fill: currentColor; display: block; }
      button { font: inherit; }
      .feature-row {
        min-height: var(--feature-height, 42px);
        display: grid;
        grid-template-columns: var(--feature-height, 42px) minmax(80px, 1fr) var(--feature-height, 42px);
        align-items: center;
        gap: 8px;
        padding: 0 4px;
        border-radius: var(--feature-border-radius, 12px);
        background: var(--feature-color, var(--secondary-background-color));
      }
      .feature-button,
      .icon-button,
      .close-button {
        border: 0;
        color: var(--primary-text-color);
        background: transparent;
        border-radius: 50%;
        display: inline-grid;
        place-items: center;
        cursor: pointer;
        transition: background-color 120ms ease, color 120ms ease, transform 120ms ease;
      }
      .feature-button { width: 38px; height: 38px; position: relative; }
      .icon-button { width: 36px; height: 36px; flex: 0 0 auto; }
      .close-button { width: 40px; height: 40px; }
      .feature-button:hover:not(:disabled),
      .icon-button:hover:not(:disabled),
      .close-button:hover { background: var(--secondary-background-color); }
      .feature-button:active:not(:disabled),
      .icon-button:active:not(:disabled) { transform: scale(.94); }
      button.active { color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 14%, transparent); }
      button:disabled, input:disabled { opacity: .38; cursor: default; }
      .count {
        position: absolute;
        right: 0;
        top: 1px;
        min-width: 16px;
        height: 16px;
        padding: 0 4px;
        display: grid;
        place-items: center;
        border-radius: 9px;
        background: var(--primary-color);
        color: var(--text-primary-color, white);
        font-size: 10px;
        font-weight: 700;
        line-height: 1;
      }
      .volume-slider {
        width: 100%;
        min-width: 70px;
        height: 4px;
        margin: 0;
        appearance: none;
        border-radius: 2px;
        outline: none;
        background: linear-gradient(
          to right,
          var(--primary-color) 0 var(--volume-percent),
          var(--divider-color) var(--volume-percent) 100%
        );
      }
      .volume-slider::-webkit-slider-thumb {
        appearance: none;
        width: 18px;
        height: 18px;
        border: 2px solid var(--card-background-color, white);
        border-radius: 50%;
        background: var(--primary-color);
        box-shadow: 0 1px 4px rgba(0, 0, 0, .28);
        cursor: pointer;
      }
      .volume-slider::-moz-range-thumb {
        width: 16px;
        height: 16px;
        border: 2px solid var(--card-background-color, white);
        border-radius: 50%;
        background: var(--primary-color);
        box-shadow: 0 1px 4px rgba(0, 0, 0, .28);
        cursor: pointer;
      }
      dialog {
        width: min(580px, calc(100vw - 28px));
        max-height: min(760px, calc(100vh - 28px));
        padding: 0;
        border: 0;
        border-radius: 22px;
        color: var(--primary-text-color);
        background: var(--card-background-color, var(--ha-card-background));
        box-shadow: 0 18px 54px rgba(0, 0, 0, .34);
        overflow: hidden;
      }
      dialog::backdrop { background: rgba(0, 0, 0, .52); backdrop-filter: blur(2px); }
      .dialog-shell { padding: 20px; max-height: inherit; overflow: auto; }
      header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
      h2 { margin: 0; font-size: 22px; line-height: 1.25; font-weight: 650; }
      header p { margin: 4px 0 0; color: var(--secondary-text-color); font-size: 14px; }
      .room {
        border-radius: 16px;
        padding: 14px;
      }
      .room.master {
        padding: 17px;
        border: 2px solid var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 9%, var(--card-background-color, white));
        box-shadow: 0 5px 18px rgba(0, 0, 0, .08);
      }
      .room.slave { background: var(--secondary-background-color); border: 1px solid var(--divider-color); }
      .room-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
      .role-label {
        display: inline-block;
        margin-bottom: 4px;
        padding: 3px 8px;
        border-radius: 999px;
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 14%, transparent);
        font-size: 10px;
        font-weight: 750;
        letter-spacing: .09em;
        text-transform: uppercase;
      }
      .room-name { font-size: 16px; font-weight: 600; line-height: 1.3; }
      .master .room-name { font-size: 18px; font-weight: 700; }
      .volume-value { min-width: 42px; color: var(--secondary-text-color); font-size: 13px; text-align: right; font-variant-numeric: tabular-nums; }
      .room-controls { display: flex; align-items: center; gap: 8px; }
      .room-controls .volume-slider { flex: 1 1 auto; }
      .slave-heading { margin: 22px 2px 9px; color: var(--secondary-text-color); font-size: 12px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }
      .slave-list { display: grid; gap: 9px; }
      .message { min-height: var(--feature-height, 42px); display: grid; place-items: center; color: var(--error-color); font-size: 13px; }
      @media (max-width: 440px) {
        .dialog-shell { padding: 16px; }
        .room { padding: 12px; }
        .room.master { padding: 14px; }
        .room-controls { gap: 4px; }
        .icon-button { width: 32px; height: 32px; }
        .room-name { font-size: 15px; }
        .master .room-name { font-size: 17px; }
      }
    `;
  }

  _actionElement(event) {
    return event
      .composedPath()
      .find((item) => item instanceof HTMLElement && item.dataset?.action);
  }

  _handleClick(event) {
    const control = this._actionElement(event);
    if (!control || control.disabled) return;
    const action = control.dataset.action;
    const entityId = control.dataset.entity;
    if (action === "open-group") {
      this._dialogOpen = true;
      const dialog = this.shadowRoot.querySelector("dialog");
      if (dialog && !dialog.open) dialog.showModal();
      return;
    }
    if (action === "close") {
      this._closeDialog();
      return;
    }
    if (!entityId) return;
    if (action === "volume-down" || action === "volume-up") {
      this._callService(action.replace("-", "_"), { entity_id: entityId });
      return;
    }
    if (action === "mute") {
      const muted = Boolean(this._state(entityId)?.attributes?.is_volume_muted);
      this._callService("volume_mute", {
        entity_id: entityId,
        is_volume_muted: !muted,
      });
    }
  }

  _handleInput(event) {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || !input.dataset.volumeEntity) return;
    const percentage = Math.round(clampVolume(input.value) * 100);
    input.style.setProperty("--volume-percent", `${percentage}%`);
    const label = this.shadowRoot.querySelector(
      `[data-value-for="${CSS.escape(input.dataset.volumeEntity)}"]`,
    );
    if (label) label.textContent = `${percentage}%`;
  }

  _handleChange(event) {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || !input.dataset.volumeEntity) return;
    this._callService("volume_set", {
      entity_id: input.dataset.volumeEntity,
      volume_level: clampVolume(input.value),
    });
  }

  _callService(service, data) {
    if (!this._hass) return;
    Promise.resolve(this._hass.callService("media_player", service, data)).catch(
      (error) => console.error(`CasaTunes ${service} failed`, error),
    );
  }

  _closeDialog() {
    this._dialogOpen = false;
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog?.open) dialog.close();
  }
}

if (!customElements.get(FEATURE_TYPE)) {
  customElements.define(FEATURE_TYPE, CasaTunesGroupVolumeCardFeature);
}

window.customCardFeatures = window.customCardFeatures || [];
if (!window.customCardFeatures.some((feature) => feature.type === FEATURE_TYPE)) {
  window.customCardFeatures.push({
    type: FEATURE_TYPE,
    name: "CasaTunes group volume",
    configurable: false,
    isSupported: (hass, context) => {
      const state = context.entity_id ? hass.states[context.entity_id] : undefined;
      return Boolean(state?.attributes?.casatunes_group_volume);
    },
  });
}
