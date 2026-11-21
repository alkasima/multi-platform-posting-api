/* PostPilot — landing page behaviour */
(() => {
  "use strict";

  const PLATFORM_META = {
    Bluesky: { brand: "#1d9bf0", initial: "B" },
    "DEV Community": { brand: "#f97316", initial: "D" },
    Mastodon: { brand: "#6364ff", initial: "M" },
    Telegram: { brand: "#229ed9", initial: "T" },
    Discord: { brand: "#5865f2", initial: "D" },
  };

  const $ = (selector) => document.querySelector(selector);

  /* ---------------------------------------------------------------- health */
  const healthPill = $("#health-pill");
  const healthText = $("#health-text");

  async function loadHealth() {
    try {
      const response = await fetch("/health");
      const data = await response.json();
      healthPill.classList.add("is-online");
      healthPill.classList.remove("is-offline");
      healthText.textContent = `API online · v${data.version}${data.demo_mode ? " · demo" : ""}`;
    } catch {
      healthPill.classList.add("is-offline");
      healthPill.classList.remove("is-online");
      healthText.textContent = "API offline";
    }
  }

  /* ------------------------------------------------------------- platforms */
  const platformGrid = $("#platform-grid");

  function skeletonMarkup() {
    return Array.from({ length: 5 }, () => '<div class="skeleton"></div>').join("");
  }

  function renderPlatform(platform) {
    const meta = PLATFORM_META[platform.platform] || {
      brand: "#7c5cff",
      initial: platform.platform.charAt(0),
    };

    let badge;
    let metaText;
    let metaTitle = "";

    if (platform.simulated) {
      badge = '<span class="badge badge-sim">Simulated</span>';
      metaText = "No network calls";
    } else if (platform.configured) {
      badge = '<span class="badge badge-ok">Ready</span>';
      const count = platform.required_settings.length;
      metaText = `${count} credential${count === 1 ? "" : "s"} set`;
    } else {
      badge = '<span class="badge badge-warn">Needs setup</span>';
      metaText = platform.missing_settings.join(", ");
      metaTitle = ` title="${platform.missing_settings.join(", ")}"`;
    }

    const docs = platform.docs
      ? `<a class="platform-docs" href="${platform.docs}" target="_blank" rel="noopener">API docs <span aria-hidden="true">↗</span></a>`
      : '<span class="platform-docs">Simulated platform</span>';

    return `
      <article class="platform-card" style="--brand:${meta.brand}">
        <div class="platform-top">
          <span class="platform-avatar" aria-hidden="true">${meta.initial}</span>
          ${badge}
        </div>
        <h3>${platform.platform}</h3>
        <p class="platform-meta"${metaTitle}>${metaText}</p>
        ${docs}
      </article>`;
  }

  async function loadPlatforms() {
    platformGrid.innerHTML = skeletonMarkup();
    try {
      const response = await fetch("/platforms");
      const data = await response.json();
      platformGrid.innerHTML = data.platforms.map(renderPlatform).join("");
    } catch {
      platformGrid.innerHTML =
        '<p class="platform-error">Could not load platform status.</p>';
    }
  }

  $("#refresh-platforms").addEventListener("click", loadPlatforms);

  /* ----------------------------------------------------------- JSON output */
  function escapeHtml(value) {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function highlightJson(json) {
    const escaped = escapeHtml(json);
    return escaped.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (match) => {
        let cls = "json-number";
        if (/^"/.test(match)) {
          cls = /:$/.test(match) ? "json-key" : "json-string";
        } else if (/true|false/.test(match)) {
          cls = "json-boolean";
        } else if (/null/.test(match)) {
          cls = "json-null";
        }
        return `<span class="${cls}">${match}</span>`;
      }
    );
  }

  /* ----------------------------------------------------------------- form */
  const form = $("#demo-form");
  const textarea = $("#message");
  const counter = $("#char-count");
  const errorBox = $("#form-error");
  const submitButton = $("#submit-btn");
  const spinner = submitButton.querySelector(".spinner");
  const submitLabel = submitButton.querySelector(".btn-label");
  const resultPanel = $("#result");
  const resultBody = $("#result-body");
  const resultTitle = $("#result-title");
  const copyButton = $("#copy-btn");

  function updateCounter() {
    const length = textarea.value.length;
    counter.textContent = `${length} / 200`;
    counter.classList.toggle("is-near", length > 180);
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function renderResult(ok, data) {
    resultPanel.hidden = false;
    resultPanel.classList.toggle("is-success", Boolean(data.success));
    resultPanel.classList.toggle("is-failed", !data.success);

    const results = Array.isArray(data.results) ? data.results : [];
    const failed = results.filter((item) => item.status === "failed").length;

    if (data.success && failed > 0) {
      resultTitle.textContent = `Completed · ${failed} failed`;
    } else if (data.success) {
      resultTitle.textContent = "All platforms succeeded";
    } else if (data.error === "validation_error") {
      resultTitle.textContent = "Validation error";
    } else {
      resultTitle.textContent = "Request failed";
    }

    resultBody.innerHTML = highlightJson(JSON.stringify(data, null, 2));
    resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  textarea.addEventListener("input", updateCounter);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const message = textarea.value.trim();

    if (!message) {
      showError("Message cannot be empty.");
      return;
    }
    if (message.length > 200) {
      showError(`Message must be 200 characters or fewer (currently ${message.length}).`);
      return;
    }

    const links = message.match(/https?:\/\/[^\s<>"'`]+/gi) || [];
    if (links.length !== 1) {
      showError(`Exactly one CTA link is required (found ${links.length}).`);
      return;
    }

    submitButton.disabled = true;
    submitLabel.textContent = "Posting…";
    spinner.hidden = false;

    try {
      const response = await fetch("/posting", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await response.json();
      renderResult(response.ok, data);
    } catch (error) {
      renderResult(false, {
        success: false,
        error: "network_error",
        message: String(error),
      });
    } finally {
      submitButton.disabled = false;
      submitLabel.textContent = "Post to all platforms";
      spinner.hidden = true;
    }
  });

  copyButton.addEventListener("click", async () => {
    const previous = copyButton.textContent;
    try {
      await navigator.clipboard.writeText(resultBody.textContent);
      copyButton.textContent = "Copied ✓";
    } catch {
      copyButton.textContent = "Copy failed";
    }
    window.setTimeout(() => {
      copyButton.textContent = previous;
    }, 1600);
  });

  /* ----------------------------------------------------------------- init */
  updateCounter();
  loadHealth();
  loadPlatforms();
})();