import json
import re
import subprocess
from pathlib import Path

import pytest

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


def test_send_keeps_previous_controls_until_success():
    send = JS.split("async function send(body, label) {", 1)[1].split(
        "async function confirm(button)", 1
    )[0]
    assert "const previousControls = document.querySelectorAll('.chips,.confirm-area')" in send
    assert send.index("await renderTurn(result, reply)") < send.index(
        "previousControls.forEach(el => el.remove())"
    ) < send.index("catch (err)")
    assert "loading(false)" in send


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


DOM_HARNESS = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {source, scenario} = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
class Element {
  constructor(tag, className = '') {
    Object.assign(this, {tag, className, children: [], dataset: {}, style: {},
      hidden: false, disabled: false, value: '', ownText: ''});
    this.classList = {
      add: name => { this.className += ' ' + name; },
      remove: name => { this.className = this.className.split(' ').filter(x => x !== name).join(' '); }
    };
  }
  set textContent(value) { this.replaceChildren(); this.ownText = String(value); }
  get textContent() { return this.ownText + this.children.map(x => x.textContent).join(''); }
  append(...items) {
    for (const child of items) { child.remove(); child.parent = this; this.children.push(child); }
  }
  remove() {
    if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this);
    this.parent = null;
  }
  replaceChildren(...items) {
    for (const child of [...this.children]) child.remove();
    this.ownText = '';
    this.append(...items);
  }
  setAttribute(name, value) { this[name] = value; }
  matches(selector) {
    const parts = selector.trim().split(/\s+/);
    const last = parts.pop();
    const attribute = /^\[data-(\w+)="([^"]+)"\]$/.exec(last);
    const match = last.startsWith('.') ? this.className.split(/\s+/).includes(last.slice(1))
      : attribute ? this.dataset[attribute[1]] === attribute[2] : this.tag === last;
    if (!match || !parts.length) return match;
    for (let p = this.parent; p; p = p.parent) if (p.matches(parts.join(' '))) return true;
    return false;
  }
  querySelectorAll(selector) {
    const descendants = this.children.flatMap(x => [x, ...x.querySelectorAll('*')]);
    return selector === '*' ? descendants
      : descendants.filter(x => selector.split(',').some(s => x.matches(s)));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const root = new Element('main');
const ids = {};
for (const id of ['mode', 'send', 'message', 'toast', 'thread', 'welcome',
                  'agents', 'workspace', 'composer', 'mode-badge', 'live-hint']) {
  ids[id] = new Element(id === 'message' ? 'textarea' : 'div');
  root.append(ids[id]);
}
ids.mode.value = 'demo';
ids.agents.hidden = ids.toast.hidden = true;
ids.toast.append(new Element('p'), new Element('button'));
const kinds = ['registration', 'hotel', 'transport'];
for (const kind of kinds) {
  const card = new Element('article', 'agent');
  card.dataset.agent = kind;
  for (const cls of ['status', 'preview', 'steps', 'handoff']) card.append(new Element('div', cls));
  ids.agents.append(card);
}
const document = {
  getElementById: id => { assert.ok(ids[id], id); return ids[id]; },
  createElement: tag => new Element(tag),
  querySelectorAll: selector => root.querySelectorAll(selector),
  querySelector: selector => root.querySelector(selector)
};
const responses = [], calls = [], timers = [];
const respond = (path, data, status = 200) => responses.push({path, data, status});
respond('/api/health', {mode: 'demo', live_ready: {linkup: false, h: false}});
vm.runInNewContext(source, {document, URL,
  location: {href: 'https://runai.example/', origin: 'https://runai.example'},
  matchMedia: () => ({matches: true}),
  setTimeout: fn => { timers.push(fn); return timers.length; },
  clearTimeout: () => {},
  fetch: async (path, options) => {
    calls.push({path, body: options?.body && JSON.parse(options.body)});
    const response = responses.shift();
    assert.ok(response, 'Unexpected request: ' + path);
    assert.equal(path, response.path);
    return {ok: response.status < 400, json: async () => response.data};
  }
});
const flush = async () => { for (let i = 0; i < 5; i++) await new Promise(setImmediate); };
const submit = async value => {
  ids.message.value = value;
  ids.composer.onsubmit({preventDefault() {}});
  await flush();
};
const turn = ready => ({message: ready ? 'Plan prêt' : 'Choisissez une course',
  question: ready ? null : 'Laquelle ?', error: null, ready_to_confirm: ready,
  candidates: [{name: 'Course synthétique', race_date: '2027-04-08', distance_km: 42.195}],
  draft: ready ? {race: {name: 'Course synthétique', race_date: '2027-04-08'},
    origin_city: 'Paris', nights: 2, budget_eur: 450} : {},
  suggestions: [{id: 'choice', label: 'Choisir', kind: 'choose_race', provenance: 'synthetic'}]});
const mission = ready => ({id: 'test-mission', turns: [turn(ready)], events: [], results: []});
(async () => {
  await flush();
  if (scenario === 'empty') {
    await submit('   ');
    assert.equal(calls.length, 1);
    assert.equal(root.querySelectorAll('.message').length, 0);
    respond('/api/missions', {id: 'test-mission', turns: [{}]});
    await submit('une course');
    assert.ok(ids.thread.textContent.includes('Aucune proposition pour le moment'));
    assert.equal(root.querySelector('.confirm'), null);
    assert.equal(ids.agents.hidden, true);
  } else {
    respond('/api/missions', mission(scenario === 'error'), 201);
    await submit('un marathon au printemps');
    assert.deepEqual(calls[1].body, {text: 'un marathon au printemps', mode: 'demo'});
    assert.ok(ids.thread.textContent.includes('Course synthétique'));
    assert.equal(ids.agents.hidden, true);
    const choice = root.querySelector('.chip');
    if (scenario === 'error') {
      const controls = root.querySelectorAll('.chips,.confirm-area');
      respond('/api/missions/test-mission/messages', {detail: 'Choix invalide'}, 422);
      await choice.onclick();
      assert.equal(ids.toast.hidden, false);
      assert.equal(ids.toast.querySelector('p').textContent, 'Choix invalide');
      for (const control of controls) assert.ok(control.parent, 'Retry control was removed');
      assert.equal(choice.disabled, false);
      assert.equal(root.querySelector('.confirm').disabled, false);
      respond('/api/missions/test-mission/messages', mission(false));
      await choice.onclick();
      assert.deepEqual(calls.at(-1).body, {suggestion_id: 'choice'});
      assert.ok(controls.every(control => !control.parent));
      assert.equal(ids.toast.hidden, true);
      assert.equal(ids.send.disabled, false);
    } else {
      assert.equal(root.querySelector('.confirm'), null);
      respond('/api/missions/test-mission/messages', mission(true));
      await choice.onclick();
      assert.deepEqual(calls.at(-1).body, {suggestion_id: 'choice'});
      assert.ok(ids.thread.textContent.includes('450 €'));
      assert.equal(ids.agents.hidden, true);
      respond('/api/missions/test-mission/confirm', {...mission(true), status: 'running'}, 202);
      const events = kinds.map((kind, i) => ({sequence: i + 1, type: 'live_frame', kind,
        frame_id: 'frame-' + kind, observed_at: '2026-11-08T20:00:00Z'}));
      respond('/api/missions/test-mission/events?after=0', events);
      respond('/api/missions/test-mission', {status: 'completed', events,
        results: kinds.map(kind => ({kind, status: 'ready_for_payment',
          handoff_url: 'https://example.org/' + kind, summary: 'Synthétique'}))});
      await root.querySelector('.confirm').onclick();
      await flush();
      assert.deepEqual(calls.find(x => x.path.endsWith('/confirm')).body, {confirmed: true});
      assert.equal(ids.agents.hidden, false);
      for (const kind of kinds) {
        const card = root.querySelector(`[data-agent="${kind}"]`);
        assert.equal(card.querySelector('.status').dataset.status, 'ready_for_payment');
        assert.equal(card.querySelector('img').src, '/api/frames/frame-' + kind);
        assert.equal(card.querySelector('.handoff').querySelector('a').href, 'https://example.org/' + kind);
      }
      assert.equal(timers.length, 0, 'Terminal snapshot must stop polling');
      assert.equal(root.querySelector('.confirm'), null);
      assert.equal(ids.toast.hidden, true);
    }
  }
  assert.equal(responses.length, 0, 'All expected responses must be consumed');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


@pytest.mark.parametrize("scenario", ["normal", "empty", "error"])
def test_executable_chat_paths(scenario):
    result = subprocess.run(
        ["node", "-e", DOM_HARNESS],
        input=json.dumps({"source": JS, "scenario": scenario}),
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
