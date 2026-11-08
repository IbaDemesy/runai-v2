"""Offline, executable browser-state regression tests. No provider requests."""

import json
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static/index.html").read_text()
JS = (ROOT / "static/app.js").read_text()
CSS = (ROOT / "static/styles.css").read_text()


def test_static_safety_and_accessibility():
    assert '<iframe' not in HTML
    assert "iframe" not in JS
    assert "live_view_url" not in JS
    assert "innerHTML" not in JS
    assert "console." not in JS
    assert 'role="log"' in HTML
    assert 'role="alert"' in HTML
    assert 'aria-expanded="false"' in HTML
    assert 'id="agents" hidden' in HTML
    assert "100dvh" in CSS
    assert "prefers-reduced-motion: reduce" in CSS
    assert "max-width: 768px" in CSS
    assert "object-fit: contain" in CSS
    assert "focus-visible" in CSS
    assert "SIMULATION SYNTHÉTIQUE" in HTML
    assert not re.search(r"https?://|@import", CSS)


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
    this.ownText = ''; this.append(...items);
  }
  setAttribute(name, value) { this[name] = value; }
  getAttribute(name) { return this[name]; }
  matches(selector) {
    const parts = selector.trim().split(/\s+/), last = parts.pop();
    const attribute = /^\[data-([\w-]+)="([^"]+)"\]$/.exec(last);
    const match = last.startsWith('.') ? this.className.split(/\s+/).includes(last.slice(1))
      : attribute ? this.dataset[attribute[1]] === attribute[2] : this.tag === last;
    if (!match || !parts.length) return match;
    for (let p = this.parent; p; p = p.parent) if (p.matches(parts.join(' '))) return true;
    return false;
  }
  querySelectorAll(selector) {
    const descendants = this.children.flatMap(x => [x, ...x.querySelectorAll('*')]);
    return selector === '*' ? descendants : descendants.filter(x => selector.split(',').some(s => x.matches(s)));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const root = new Element('main'), ids = {};
for (const id of ['mode', 'send', 'message', 'toast', 'thread', 'welcome', 'agents',
  'workspace', 'composer', 'mode-badge', 'live-hint', 'history-toggle']) {
  ids[id] = new Element(id === 'message' ? 'textarea' : 'div'); root.append(ids[id]);
}
const footnote = new Element('p', 'agent-footnote'); root.append(footnote);
ids.mode.value = 'demo'; ids.agents.hidden = ids.toast.hidden = true;
ids.toast.append(new Element('p'), new Element('button'));
const kinds = ['registration', 'hotel', 'transport'];
for (const kind of kinds) {
  const card = new Element('article', 'agent'); card.dataset.agent = kind;
  for (const cls of ['status', 'preview', 'frame-meta', 'steps', 'handoff']) card.append(new Element('div', cls));
  ids.agents.append(card);
}
const document = {getElementById: id => { assert.ok(ids[id], id); return ids[id]; },
  createElement: tag => new Element(tag), querySelectorAll: s => root.querySelectorAll(s), querySelector: s => root.querySelector(s)};
const responses = [], calls = [], timers = new Map(), images = [];
let timerId = 0, now = 1794174000000;
class Clock extends Date { static now() { return now; } }
class MockImage extends Element {
  constructor() { super('img'); images.push(this); }
  decode() { return this.decodeResult || Promise.resolve(); }
}
const respond = (path, data, status = 200) => responses.push({path, data, status});
respond('/api/health', {mode: 'demo', live_ready: {linkup: false, h: false}});
const context = {document, URL, Intl, Date: Clock, AbortController, Image: MockImage,
  location: {href: 'https://runai.example/', origin: 'https://runai.example'},
  setTimeout: (fn, ms) => { timers.set(++timerId, {fn, ms}); return timerId; },
  clearTimeout: id => timers.delete(id),
  fetch: async (path, options) => {
    calls.push({path, body: options?.body && JSON.parse(options.body)});
    const response = responses.shift(); assert.ok(response, 'Unexpected request: ' + path);
    assert.equal(path, response.path);
    const data = await response.data;
    return {ok: response.status < 400, status: response.status, json: async () => data};
  }};
vm.runInNewContext(source.replace('badge(); const initialGeneration',
  'globalThis.ui = {event, consume, poll, frameMeta, send, safeURL}; badge(); const initialGeneration'), context);
const ui = context.ui;
const flush = async () => { for (let i = 0; i < 5; i++) await new Promise(setImmediate); };
const tick = async ms => { const entry = [...timers].find(([, t]) => t.ms === ms); assert.ok(entry, 'timer ' + ms); timers.delete(entry[0]); entry[1].fn(); await flush(); };
const submit = async value => { ids.message.value = value; ids.composer.onsubmit({preventDefault() {}}); await flush(); };
const race = {id: 'race', name: 'Course synthétique', city: 'Lisbonne', country: 'Portugal', race_date: '2027-03-07', distance_km: 21.0975,
  date_status: 'official', source_urls: ['https://example.org/race'], retrieved_at: '2026-11-08T10:00:00Z', synthetic: true,
  registration_access: {account_required: true, captcha: null, note: 'RAW_PROVIDER_NOTE'}};
const turn = ready => ({message: ready ? 'Plan prêt' : 'Voici les courses proposées.', question: ready ? null : 'Laquelle vous inspire ?',
  ready_to_confirm: ready, candidates: ready ? [] : [race], draft: ready ? {race, origin_city: 'Paris', nights: 2, budget_eur: 450} : {race: null},
  suggestions: [{id: 'choice', label: 'Choisir cette course', kind: 'choose_race', provenance: 'source'},
    {id: 'launch', label: 'Lancer', kind: 'confirm', provenance: 'source'}]});
const mission = ready => ({id: 'm1', status: ready ? 'ready' : 'guiding', turns: [turn(ready)], events: [], results: [], error: null});
const frame = (kind, id, sequence) => ({kind, sequence, type: 'live_frame', frame_id: id,
  observed_at: '2026-11-08T21:40:00Z', recorded_at: '2025-04-01T12:34:56Z'});
const card = kind => root.querySelector(`[data-agent="${kind}"]`);
const loaded = async img => { await img.onload(); await flush(); };
const initial = async (ready = false) => { respond('/api/missions', mission(ready)); await submit('un semi au printemps'); };
(async () => {
  await flush();
  if (scenario === 'chronology') {
    await initial();
    const inner = root.querySelector('.assistant').querySelector('.message-content');
    assert.deepEqual(inner.children.map(x => x.className), ['message-name', 'bubble', 'candidates', 'question', 'chips']);
    assert.equal(root.querySelector('.plan-card'), null);
    assert.equal(root.querySelector('.confirm'), null, 'Suggestion cannot launch');
    assert.ok(inner.textContent.includes('21,1 km')); assert.ok(!inner.textContent.includes('21.0975'));
    assert.ok(inner.textContent.includes('7 mars 2027')); assert.ok(inner.textContent.includes('Compte requis'));
    assert.ok(!inner.textContent.includes('RAW_PROVIDER_NOTE'));
    assert.ok(!root.querySelector('.chip').textContent.includes('Course sourcée'));
    const previous = inner.textContent;
    respond('/api/missions/m1/messages', mission(true)); await root.querySelector('.chip').onclick();
    assert.equal(inner.textContent, previous, 'Do not mutate prior proposals');
    assert.ok(root.querySelector('.confirm')); assert.equal(ids.agents.hidden, true);
    assert.ok(root.querySelector('.chip').disabled);
    assert.equal(root.querySelectorAll('.assistant').length, 2);
  } else if (scenario === 'pending') {
    let resolve; const deferred = new Promise(r => { resolve = r; });
    respond('/api/missions', deferred);
    const start = performance.now(); ids.message.value = 'une course'; ids.composer.onsubmit({preventDefault() {}});
    assert.ok(performance.now() - start < 250); assert.ok(root.querySelector('.skeleton'));
    assert.ok(ids.thread.textContent.includes('dates officielles'));
    now += 21000; await tick(1000); assert.ok(ids.thread.textContent.includes('21 s écoulées'));
    resolve(mission(false)); await flush(); assert.equal(root.querySelector('.pending'), null);
  } else if (scenario === 'background') {
    respond('/api/missions', {id:'m1', status:'discovering', turns:[]}, 202); await submit('une course');
    assert.equal(calls.at(-1).body.background, true); assert.ok(root.querySelector('.pending'));
    respond('/api/missions/m1', {id:'m1', status:'discovering', turns:[]}); await tick(800);
    assert.ok(root.querySelector('.pending'));
    respond('/api/missions/m1', mission(false)); await tick(800);
    assert.equal(root.querySelectorAll('.assistant').length, 1); assert.equal(root.querySelector('.pending'), null);
  } else if (scenario === 'sync') {
    respond('/api/missions', {detail:'extra field'}, 422); respond('/api/missions', mission(false)); await submit('course');
    assert.equal(calls[1].body.background, true); assert.equal(calls[2].body.background, undefined);
    assert.ok(root.querySelector('.question'));
  } else if (scenario === 'retry') {
    respond('/api/missions', {id:'m1', status:'discovering', turns:[]}, 202); await submit('course');
    respond('/api/missions/m1', {id:'m1', status:'guiding', turns:[], error:'RAW_API_KEY_DUMP'}); await tick(800);
    assert.equal(ids.toast.hidden, false); assert.ok(!root.textContent.includes('RAW_API'));
    respond('/api/missions/m1/messages', mission(false)); await root.querySelector('.retry').onclick(); await flush();
    assert.equal(calls.at(-1).body.text, 'course'); assert.equal(root.querySelectorAll('.assistant').length, 1);
    assert.equal(root.querySelector('.pending'), null);
  } else if (scenario === 'sensitive') {
    respond('/api/missions', {id:'m1', turns:[{message:'Echo: test@example.org 4111 1111 1111 1111 password=hidden', question:'test@example.org', suggestions:[]}]});
    await submit('test@example.org 4111 1111 1111 1111 +33 6 12 34 56 78 password=hidden');
    for (const secret of ['test@example.org', '4111', '+33', 'password=hidden']) assert.ok(!root.textContent.includes(secret));
    respond('/api/missions/m1/messages', {detail:'RAW_SECRET'}, 500); await submit('continue');
    assert.ok(!root.textContent.includes('RAW_SECRET')); assert.equal(ids.toast.hidden, false);
  } else if (scenario === 'empty') {
    await submit('  '); assert.equal(calls.length, 1);
    respond('/api/missions', {id:'m1', turns:[{}]}); await submit('course');
    assert.ok(ids.thread.textContent.includes('Aucune proposition')); assert.equal(root.querySelector('.plan-card'), null);
  } else if (scenario === 'generation') {
    let resolve; respond('/api/missions', new Promise(r => {resolve = r;})); await submit('ancienne course');
    ids.mode.value = 'replay'; ids.mode.onchange(); resolve(mission(false)); await flush();
    assert.equal(root.querySelectorAll('.message').length, 0); assert.equal(ids.send.disabled, false);
    assert.ok(ids['mode-badge'].textContent.includes('REPLAY')); assert.equal(ids.agents.hidden, true);
  } else if (scenario === 'frames' || scenario === 'stale' || scenario === 'decode' || scenario === 'replay') {
    if (scenario === 'replay') { ids.mode.value = 'replay'; ids.mode.onchange(); }
    for (let i = 0; i < kinds.length; i++) {
      const kind = kinds[i];
      ui.event({kind, type:'step_started'});
      ui.event({kind, type:'live_view_available', live_view_url:'https://agp.eu.hcompany.ai/share/api/v1/trajectories/private', message:'RAW_PROMPT'});
      ui.event(frame(kind, 'first-' + kind, i+1));
      assert.equal(card(kind).querySelector('img'), null, 'Wait for image decode');
      await loaded(images.at(-1));
    }
    if (scenario === 'decode') {
      ui.event(frame('hotel', 'slow', 4)); const slow = images.at(-1);
      let decode; slow.decodeResult = new Promise(r => {decode = r;}); slow.onload(); await flush();
      assert.equal(card('hotel').querySelector('img').src, '/api/frames/first-hotel');
      ui.event(frame('hotel', 'newer', 5)); await loaded(images.at(-1)); decode(); await flush();
      assert.equal(card('hotel').querySelector('img').src, '/api/frames/newer');
      ui.event(frame('hotel','reset-late',6)); const late = images.at(-1); ids.mode.onchange(); await loaded(late);
      assert.equal(card('hotel').querySelector('img'), null);
    } else if (scenario === 'stale') {
      ui.event(frame('hotel', '404', 4)); images.at(-1).onerror();
      assert.equal(card('hotel').querySelector('img').src, '/api/frames/first-hotel');
      assert.equal(card('hotel').querySelector('.preview').dataset.state, 'stale');
      now += 21000; ui.frameMeta('transport');
      assert.equal(card('transport').querySelector('.preview').dataset.state, 'stale');
      ui.event(frame('hotel', 'recovered', 5)); await loaded(images.at(-1));
      assert.equal(card('hotel').querySelector('.preview').dataset.state, 'available');
    } else {
      for (const kind of kinds) {
        ui.event({kind,type:'live_view_available',live_view_url:'https://agp.eu.hcompany.ai/share/api/v1/trajectories/late'});
        ui.event(frame(kind, 'last-' + kind, 10)); await loaded(images.at(-1));
        ui.event({kind,status:'ready_for_payment',summary:'RAW_RESULT',live_view_url:'https://agp.eu.hcompany.ai/share/api/v1/trajectories/last',handoff_url:'https://example.org/' + kind});
        assert.equal(card(kind).querySelector('img').src, '/api/frames/last-' + kind);
        assert.equal(card(kind).querySelector('.status').dataset.status, 'ready_for_payment');
        assert.ok(card(kind).querySelector('.frame-meta').textContent.includes('Dernière capture'));
      }
      assert.equal(root.querySelectorAll('iframe').length, 0); assert.ok(!root.textContent.includes('RAW_'));
      assert.equal(calls.length,1, 'Share URLs are never fetched');
      if (scenario === 'replay') assert.ok(card('hotel').querySelector('.frame-meta').textContent.includes('12:34:56'));
    }
  } else if (scenario === 'launch') {
    await initial(true);
    respond('/api/missions/m1/confirm', {...mission(true), status:'running'}, 202);
    respond('/api/missions/m1/events?after=0', kinds.map((kind,i) => frame(kind,kind,i+1)));
    respond('/api/missions/m1', {status:'completed', results:kinds.map(kind => ({kind,status:'ready_for_payment',handoff_url:'https://example.org/' + kind}))});
    await root.querySelector('.confirm').onclick(); await flush();
    for (const img of images) await loaded(img);
    assert.equal(ids.agents.hidden,false); assert.ok(ids.workspace.className.includes('executing'));
    assert.equal(root.querySelectorAll('.confirm').length,0); assert.equal(timers.size,0);
    assert.deepEqual(calls.find(x=>x.path.endsWith('/confirm')).body,{confirmed:true});
    ids['history-toggle'].onclick(); assert.equal(ids['history-toggle'].getAttribute('aria-expanded'),'true');
    ids.mode.value='live'; ids.mode.onchange(); assert.equal(footnote.hidden,true);
    for(const kind of kinds) assert.equal(card(kind).querySelector('img'),null);
    assert.equal(ui.safeURL('https://agp.eu.hcompany.ai/share/api/v1/trajectories/id'),null);
    assert.equal(ui.safeURL('https://example.org/?token=secret'),null);
  } else if (scenario === 'disconnect') {
    await initial(true); ui.event(frame('hotel','valid',1)); await loaded(images.at(-1));
    respond('/api/missions/m1/events?after=1', {}, 500); await ui.poll(0);
    assert.equal(card('hotel').querySelector('.preview').dataset.state,'stale');
    assert.ok(root.querySelector('.retry'));
    respond('/api/missions/m1/events?after=1', [frame('hotel','reconnected',2)]);
    respond('/api/missions/m1',{results:kinds.map(kind=>({kind,status:'blocked'}))});
    root.querySelector('.retry').onclick(); await flush(); await loaded(images.at(-1));
    assert.equal(card('hotel').querySelector('img').src,'/api/frames/reconnected');
  }
  assert.equal(responses.length, 0, 'Consume expected responses');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


@pytest.mark.parametrize("scenario", [
    "chronology", "pending", "background", "sync", "retry", "sensitive", "empty",
    "generation", "frames", "stale", "decode", "replay", "launch", "disconnect",
])
def test_executable_browser_states(scenario):
    result = subprocess.run(
        ["node", "-e", DOM_HARNESS],
        input=json.dumps({"source": JS, "scenario": scenario}),
        text=True, capture_output=True, check=False, timeout=15,
    )
    assert result.returncode == 0, result.stderr
