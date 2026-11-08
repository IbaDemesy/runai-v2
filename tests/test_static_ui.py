import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static/index.html").read_text()
JS = (ROOT / "static/app.js").read_text()
CSS = (ROOT / "static/styles.css").read_text()


def test_local_assets_and_no_external_dependencies():
    for name in ("styles.css", "app.js"):
        assert f'"/static/{name}"' in HTML
        assert (ROOT / "static" / name).is_file()
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)=["\']https?://', HTML)
    assert not re.search(r"(?:@import|url\()[^;\n]*https?://", CSS)


def test_no_secrets_or_prohibited_sites():
    source = HTML + JS + CSS
    for pattern in (
        r"HAI_API_KEY\s*[:=]", r"sk-[A-Za-z0-9]{12,}", r"Bearer\s+",
        r"\b[a-f0-9]{40,}\b", r"booking\.com", r"flytap", r"\bTAP\b",
    ):
        assert not re.search(pattern, source, re.IGNORECASE)


def test_safety_labels_and_hooks():
    assert "SIMULATION SYNTHÉTIQUE" in HTML
    assert "REPLAY · enregistrement synthétique · heure originale" in JS
    assert "LIVE · agents réels · arrêt avant paiement" in JS
    assert 'id="mode-badge"' in HTML
    assert 'data-testid="chips"' in HTML
    for kind in ("registration", "hotel", "transport"):
        assert f'data-agent="{kind}"' in HTML
    assert re.search(r'id="agents"\s+hidden', HTML)


def test_confirmation_is_dynamic_and_explicit():
    assert 'class="confirm"' not in HTML
    assert "if (ready)" in JS
    assert "ready_to_confirm === true" in JS
    assert "confirmation_required === true" in JS
    assert re.search(r"\{\s*confirmed:\s*true\s*\}", JS)


def test_accessible_responsive_conversation_and_safe_previews():
    assert 'role="log"' in HTML
    assert re.search(r'<textarea\s+id="message"', HTML)
    assert 'role="alert"' in HTML
    assert "100dvh" in CSS
    assert re.search(r"prefers-reduced-motion:\s*reduce", CSS)
    assert re.search(r"max-width:\s*768px", CSS)
    assert "focus-visible" in CSS
    assert "!e.shiftKey" in JS
    assert "allow-scripts allow-same-origin" in JS
    assert "no-referrer" in JS
    assert "noopener noreferrer" in JS
    assert "['http:', 'https:']" in JS


def test_empty_error_and_terminal_paths_present():
    assert "Aucune proposition pour le moment" in JS
    assert "Aperçu indisponible" in HTML
    assert "Array.isArray(detail)" in JS
    assert "if (!response.ok)" in JS
    assert "terminal.has(raw.status)" in JS
    assert "Math.max(after, sequence)" in JS


def test_live_view_requires_cross_origin_http_url():
    assert "new URL(value, location.href)" in JS
    assert "url.origin !== location.origin" in JS
    assert "const view = safeViewURL(e.live_view_url)" in JS
    assert "if (view && state.view !== view)" in JS
    assert "if (e.live_view_url != null && !view && state.view)" in JS


def test_guided_mission_contract():
    assert "envelope.turns?.at(-1)" in JS
    assert "data.draft || data.plan || envelope.trip" in JS
    assert "suggestion.kind === 'confirm' ? confirm(button)" in re.sub(r"\s+", " ", JS)
    assert "const snapshot = await api(" in JS
    assert "consume(snapshot)" in JS
    assert "e.recorded_at" in JS
    assert "p.arrival_date" in JS
    assert "p.departure_date" in JS
    assert "api('/api/health')" in JS
    assert "health.live_ready" in JS
