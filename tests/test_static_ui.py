"""Offline, executable browser-state regression tests. No provider requests."""

import json
import re
import subprocess
from pathlib import Path

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


def test_svg_flags_and_live_stage_contract():
    assert "fromCodePoint" not in JS
    assert "127397" not in JS
    assert not re.search(r"[\U0001f1e6-\U0001f1ff]", JS)
    assert "createElementNS" in JS
    assert "Date.parse(state.observed)" in JS
    assert "age * 1000 >= FRESH_MS" in JS
    assert "const FRESH_MS = 15000" in JS
    assert "clearTimeout(state.freshTimer)" in JS
    assert "browser-skeleton" in CSS
    assert "#agents[data-synthetic='true'] .preview:not([data-state='ended'])" not in CSS
    assert "position: sticky; bottom: 0" in CSS
    assert HTML.index('class="agent-grid"') < HTML.index('id="coverage"')
    assert "[data-view='coverage'] .agent-grid { display: none" not in CSS


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
  setAttribute(name, value) { this[name] = value; if (name === 'class') this.className = value; }
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
  'workspace', 'composer', 'mode-badge', 'live-hint', 'history-toggle', 'mission-banner', 'coverage']) {
  ids[id] = new Element(id === 'message' ? 'textarea' : 'div'); root.append(ids[id]);
}
const footnote = new Element('p', 'agent-footnote'); root.append(footnote);
ids.mode.value = 'demo'; ids.agents.hidden = ids.toast.hidden = true;
ids.toast.append(new Element('p'), new Element('button'));
const kinds = ['registration', 'hotel', 'transport'];
for (const kind of kinds) {
  const card = new Element('article', 'agent'); card.dataset.agent = kind;
  for (const cls of ['status', 'site', 'stepper', 'preview', 'live-badge', 'focus-toggle', 'frame-meta', 'steps', 'handoff']) card.append(new Element('div', cls));
  ids.agents.append(card);
}
const document = {getElementById: id => { assert.ok(ids[id], id); return ids[id]; },
  createElement: tag => new Element(tag), createElementNS: (ns, tag) => new Element(tag),
  querySelectorAll: s => root.querySelectorAll(s), querySelector: s => root.querySelector(s)};
const responses = [], calls = [], timers = new Map(), images = [], listeners = {};
let timerId = 0, now = 1794174000000;
class Clock extends Date { static now() { return now; } }
class MockImage extends Element {
  constructor() { super('img'); images.push(this); }
  decode() { return this.decodeResult || Promise.resolve(); }
}
const respond = (path, data, status = 200) => responses.push({path, data, status});
respond('/api/health', {mode: 'demo', live_ready: {linkup: false, h: false}});
const context = {document, URL, Intl, Date: Clock, AbortController, Image: MockImage, addEventListener: (type, fn) => { listeners[type] = fn; },
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
  if (scenario === 'polish') {
    const result = mission(true); result.language = 'en';
    result.turns[0].message = 'Plan — accès inconnu';
    result.turns[0].suggestions[0].label = 'Choice — access unknown';
    result.turns[0].draft.race.source_urls = ['https://example.org/race', 'https://www.example.org/other'];
    result.turns[0].draft.race.country_code = 'PT';
    respond('/api/missions', result); await submit('course');
    const inner = root.querySelector('.assistant').querySelector('.message-content');
    assert.equal(inner.children.at(-1).className, 'confirm-area');
    assert.ok(inner.children.indexOf(inner.querySelector('.chips')) < inner.children.indexOf(inner.querySelector('.confirm-area')));
    assert.equal(inner.querySelectorAll('.source-badge').length, 1);
    assert.ok(!inner.textContent.includes('accès inconnu')); assert.ok(!inner.textContent.includes('access unknown'));
    assert.ok(inner.textContent.includes('Arrival') || inner.textContent.includes('Origin'));
    assert.ok(inner.textContent.includes('Confirm plan'));
    assert.equal(inner.querySelector('svg').getAttribute('aria-label'), 'PT'); assert.ok(/in \d+ days/.test(inner.textContent));
    const hooks = context.__runai;
    for (const code of ['no_site_coverage', 'policy_denied', 'date_mismatch', 'no_inventory', 'sold_out', 'registration_closed', 'login_required', 'captcha', 'consent_required', 'unreviewed_redirect', 'over_budget', 'step_limit', 'session_failed', 'timeout', 'unsafe_claim', 'provider_error']) {
      assert.equal(hooks.reasons[code].length, 4); assert.ok(hooks.reasons[code].every(x => x.length > 10));
      hooks.setLanguage('fr'); assert.equal(hooks.reason(code,'blocked'), hooks.reasons[code][0]);
      hooks.setLanguage('en');
      ui.event({kind:'hotel', status:'blocked', reason_code:code, summary:'RAW_JSON_LOG', handoff_url:'https://example.org/hotel'});
      assert.equal(card('hotel').querySelector('.steps').textContent, hooks.reasonCopy(code, 'blocked', 'hotel').join(''));
      assert.ok(card('hotel').querySelector('.steps').textContent.includes(hooks.reasons[code][3]));
      assert.ok(card('hotel').querySelector('.handoff').textContent.includes('Continue on example.org'));
    }
    for (const status of ['blocked', 'failed', 'cancelled']) {
      ui.event({kind:'transport', status, reason_code:'unknown'});
      assert.ok(card('transport').querySelector('.steps').textContent.startsWith(hooks.reason('unknown', status)));
      assert.ok(card('transport').textContent.includes('No verified site'));
      assert.ok(!card('transport').textContent.includes('Waiting for'));
    }
    ui.event({kind:'registration', type:'step_started'});
    ui.event(frame('registration','old',1)); await loaded(images.at(-1));
    now += 30000; ui.frameMeta('registration');
    assert.ok(card('registration').querySelector('.live-badge').textContent.includes('AGENT WORKING'));
    assert.ok(!card('registration').textContent.includes('interrupted'));
    ui.event({kind:'registration', status:'failed'});
    assert.ok(card('registration').querySelector('.live-badge').textContent.includes('tracking interrupted'));
    assert.ok(!root.textContent.includes('RAW_JSON_LOG'));
    hooks.setLanguage('fr');
    assert.equal(hooks.reason('captcha','blocked'), hooks.reasons.captcha[0]);
    assert.notEqual(hooks.reason(null,'blocked'), hooks.reason(null,'failed'));
    const titles = Object.keys(hooks.reasons).filter(code => !code.startsWith('checkpoint_')).map(code => hooks.reason(code, 'blocked'));
    assert.equal(new Set(titles).size, 16, 'Each reason code has a specific sentence');
    assert.equal(hooks.reason('sold_out', 'blocked', 'registration'), 'Course complète.');
    assert.equal(hooks.reason('no_inventory', 'blocked'), 'Plus de disponibilité à ces dates.');
  } else if (scenario === 'chronology') {
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
    const assistants = root.querySelectorAll('.assistant');
    const nextQuestion = mission(false); nextQuestion.turns[0].question = 'D’où partez-vous ?';
    respond('/api/missions/m1/messages', nextQuestion); await submit('autre proposition');
    const latest = root.querySelectorAll('.assistant').at(-1);
    assert.ok(ids.thread.children.indexOf(latest) > ids.thread.children.indexOf(assistants[0]));
    assert.ok(ids.thread.children.indexOf(latest) > ids.thread.children.indexOf(assistants[1]));
    assert.equal(latest.querySelector('.question').textContent, 'D’où partez-vous ?');
    assert.equal(inner.querySelector('.question').textContent, 'Laquelle vous inspire ?');
    assert.equal(latest.querySelector('.chips').getAttribute('role'), 'group');
    assert.ok(latest.querySelector('.chip').getAttribute('aria-describedby'));
  } else if (scenario === 'uncertain') {
    const result = mission(false); result.turns[0].draft = {race: {...race, race_date: null, date_status: 'unknown'}};
    respond('/api/missions', result); await submit('une course');
    const inner = root.querySelector('.assistant').querySelector('.message-content');
    assert.deepEqual(inner.children.map(x => x.className), ['message-name', 'bubble', 'plan-card', 'candidates', 'question', 'chips']);
    assert.equal(root.querySelector('.confirm'), null);
  } else if (scenario === 'english') {
    const english = mission(false); english.turns[0].message = "Here's your race.";
    english.turns[0].question = 'Which one catches your eye?';
    respond('/api/missions', english); await submit('I want a half marathon in spring');
    assert.ok(ids.thread.textContent.includes('7 March 2027'));
    assert.ok(ids.thread.textContent.includes('21.1 km'));
    assert.ok(!ids.thread.textContent.includes('mars'));
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
        assert.ok(card(kind).querySelector('.live-badge').textContent.includes('Dernière capture'));
        assert.ok(card(kind).querySelector('.handoff').textContent.includes('à vous de payer sur example.org'));
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
    assert.equal(ui.safeURL('https://example.org/register?race=123&lang=fr'), 'https://example.org/register?race=123&lang=fr');
    assert.equal(ui.safeURL('https://example.org/register?email=runner%40example.org'), null);
    assert.equal(ui.safeURL('https://example.org/register?booking_id=ABC123'), null);
    assert.equal(ui.safeURL('http://example.org/register'), null);
  } else if (scenario === 'snapshot-error') {
    await initial(true); ui.event({kind:'hotel',type:'step_started'});
    ui.event(frame('hotel','valid',1)); await loaded(images.at(-1));
    respond('/api/missions/m1/events?after=1', []);
    respond('/api/missions/m1', {}, 500); await ui.poll(0);
    assert.ok(!card('hotel').querySelector('.live-badge').textContent.includes('interrompu'));
    assert.ok(card('hotel').querySelector('.live-badge').textContent.includes('AGENT AU TRAVAIL'));
  } else if (scenario === 'disconnect') {
    await initial(true); ui.event(frame('hotel','valid',1)); await loaded(images.at(-1));
    respond('/api/missions/m1/events?after=1', {}, 500); await ui.poll(0);
    assert.equal(card('hotel').querySelector('.preview').dataset.state,'stale');
    assert.ok(card('hotel').querySelector('.live-badge').textContent.includes('suivi interrompu'));
    assert.ok(root.querySelector('.retry'));
    respond('/api/missions/m1/events?after=1', [frame('hotel','reconnected',2)]);
    respond('/api/missions/m1',{results:kinds.map(kind=>({kind,status:'blocked'}))});
    root.querySelector('.retry').onclick(); await flush(); await loaded(images.at(-1));
    assert.equal(card('hotel').querySelector('img').src,'/api/frames/reconnected');
  }
  else if (scenario === 'welcome') {
    const hooks = context.__runai; hooks.setLanguage('en');
    assert.equal(hooks.translate('On prépare '), 'We handle '); assert.equal(hooks.translate(' le reste.'), ' the rest.');
    hooks.setLanguage('fr'); assert.equal(hooks.translate('On prépare '), 'On prépare ');
  } else if (scenario === 'fr-detect') {
    const hooks = context.__runai; hooks.setLanguage('en');
    let resolve; respond('/api/missions', new Promise(r => { resolve = r; }));
    await submit('un marathon au printemps en Italie');
    assert.ok(ids.thread.textContent.includes('VOTRE COPILOTE')); assert.ok(ids.thread.textContent.includes('dates officielles'));
    assert.ok(!ids.thread.textContent.includes('YOUR COPILOT'));
    for (const [text, expected] of [['le semi de Lisbonne', 'fr'], ['un trail en Suisse cet été', 'fr'], ['I want a half marathon in spring', 'en'], ['a trail race in Switzerland this summer', 'en']])
      assert.equal(hooks.detectLanguage(text), expected, text);
    resolve(mission(false)); await flush();
  } else if (scenario === 'fresh') {
    ids.mode.value = 'live'; ids.mode.onchange();
    ui.event({kind:'hotel', type:'step_started'}); ui.event(frame('hotel', 'f1', 1)); await loaded(images.at(-1));
    const badge = card('hotel').querySelector('.live-badge');
    assert.equal(badge.textContent, 'EN DIRECT'); assert.equal(badge.hidden, false);
    now += 14000; ui.frameMeta('hotel'); assert.equal(badge.textContent, 'EN DIRECT');
    now += 2000; ui.frameMeta('hotel');
    assert.equal(badge.textContent, 'AGENT AU TRAVAIL'); assert.equal(badge.dataset.tone, 'working');
    assert.ok(card('hotel').querySelector('.steps').textContent.includes('image il y a 16 s'));
    now += 40000; ui.frameMeta('hotel'); assert.equal(badge.textContent, 'AGENT AU TRAVAIL');
    assert.ok(card('hotel').querySelector('.steps').textContent.includes('image il y a 56 s'));
    assert.equal(card('hotel').querySelector('.preview').dataset.state, 'stale');
    ui.event({...frame('hotel', 'f2', 2), observed_at:new Date(now).toISOString()}); await loaded(images.at(-1)); assert.equal(badge.textContent, 'EN DIRECT');
    ids.mode.value = 'demo'; ids.mode.onchange();
    ui.event({kind:'hotel', type:'step_started'}); ui.event(frame('hotel', 'd1', 1)); await loaded(images.at(-1));
    assert.ok(!badge.textContent.includes('DIRECT')); assert.ok(badge.textContent.includes('SYNTHÉTIQUE'));
    assert.ok(!card('hotel').textContent.includes('EN DIRECT'));
  } else if (scenario === 'never-started') {
    ui.event({kind:'hotel', type:'step_started'}); ui.event({kind:'hotel', status:'blocked', reason_code:'no_inventory'});
    const meta = card('hotel').querySelector('.frame-meta').textContent;
    assert.ok(meta.includes('Non démarré'), meta); assert.ok(!meta.includes('Durée 0'));
    assert.ok(card('hotel').querySelector('.steps').textContent.includes('Plus de disponibilité'));
    ui.event({kind:'transport', type:'step_started'}); ui.event({kind:'transport', type:'step_progress', message:'Browsing reviewed site'});
    now += 65000; ui.frameMeta('transport'); assert.ok(card('transport').querySelector('.frame-meta').textContent.includes('Durée 1 min 05'));
    assert.equal(ids.coverage.hidden, true);
  } else if (scenario === 'coverage') {
    await initial(true);
    kinds.forEach(kind => ui.event({kind, type:'step_started'}));
    kinds.forEach(kind => ui.event({kind, status:'failed', reason_code:'provider_error'}));
    assert.equal(ids.agents.dataset.view, 'summary', 'Provider failures are not a coverage gap');
    assert.equal(ids.coverage.hidden, false); assert.ok(ids.coverage.textContent.includes('relais'));
    assert.equal(ids.coverage.querySelectorAll('.summary-list li').length, 3);
    ids.mode.onchange(); await initial(true);
    kinds.forEach(kind => ui.event({kind, type:'step_started'}));
    kinds.forEach(kind => { assert.equal(ids.coverage.hidden, true); ui.event({kind, status:'blocked', reason_code:'no_site_coverage', summary:'RAW_SUMMARY'}); });
    assert.equal(ids.coverage.hidden, false); assert.equal(ids.agents.dataset.view, 'coverage');
    assert.equal(ids['mission-banner'].hidden, true);
    const chips = ids.coverage.querySelectorAll('.chip'); assert.equal(chips.length, 3);
    assert.ok(!root.textContent.includes('RAW_SUMMARY'));
    respond('/api/missions', mission(false)); await chips[0].onclick(); await flush();
    assert.equal(calls.at(-1).path, '/api/missions'); assert.ok(calls.at(-1).body.text.includes('autre course'));
    assert.ok(!ids.coverage.textContent.includes('autre ville que'));
    assert.equal(ids.agents.hidden, true); assert.equal(ids.coverage.hidden, true);
  } else if (scenario === 'success') {
    await initial(true);
    kinds.forEach(kind => { ui.event({kind, type:'step_started'}); ui.event({kind, type:'step_progress', message:'Browsing'}); });
    ui.event({kind:'hotel', status:'ready_for_payment', summary:'Room total 312 € RAW', handoff_url:'https://example.org/hotel?checkin=2027-03-06'});
    const cta = card('hotel').querySelector('.cta'); assert.equal(cta.href, 'https://example.org/hotel?checkin=2027-03-06');
    assert.equal(cta.target, '_blank'); assert.ok(cta.textContent.includes('à vous de payer sur example.org'));
    assert.ok(card('hotel').textContent.includes('312 €')); assert.ok(!card('hotel').textContent.includes('RAW'));
    ui.event({kind:'registration', status:'ready_for_payment', handoff_url:'https://example.org/reg?token=abc'});
    assert.equal(card('registration').querySelector('.cta'), null);
    assert.equal(ids['mission-banner'].hidden, true);
    ui.event({kind:'transport', status:'ready_for_payment', handoff_url:'https://example.org/train'});
    assert.equal(ids['mission-banner'].hidden, false); assert.ok(ids['mission-banner'].textContent.includes('3/3') || ids['mission-banner'].textContent.includes('Tout est prêt'));
    ui.event({kind:'registration', status:'ready_for_payment', handoff_url:'https://example.org/reg'});
    assert.ok(ids['mission-banner'].textContent.includes('Tout est prêt avant paiement'));
    assert.equal(card('transport').querySelector('.stepper').children.at(-1).dataset.state, 'done');
  } else if (scenario === 'preparation') {
    const result = mission(false);
    result.turns[0].candidates = [{...race, id: 'a', preparation: {registration: {status: 'covered', site: 'example.org'}, hotel: true, transport: 'sold_out'}}, {...race, id: 'b'}];
    respond('/api/missions', result); await submit('une course');
    const cards = root.querySelectorAll('.candidate');
    assert.equal(cards[0].querySelectorAll('.prep-badge').length, 3);
    assert.ok(cards[0].textContent.includes('Inscription ✓')); assert.ok(cards[0].textContent.includes('Hôtel ✓'));
    assert.equal(cards[1].querySelectorAll('.prep-badge').length, 0); assert.equal(cards[1].querySelector('.prep'), null);
    assert.equal(cards[0].querySelector('svg').dataset.country, 'PT');
  } else if (scenario === 'crossfade') {
    ids.mode.value = 'live'; ids.mode.onchange();
    ui.event({kind:'hotel', type:'step_started'}); ui.event(frame('hotel', 'c1', 1)); await loaded(images.at(-1));
    const preview = card('hotel').querySelector('.preview');
    assert.equal(preview.querySelector('img').className, 'frame first-frame');
    ui.event(frame('hotel', 'c2', 2)); await loaded(images.at(-1));
    const both = preview.querySelectorAll('img'); assert.equal(both.length, 2);
    assert.equal(both[0].src, '/api/frames/c2'); assert.equal(both[0].className, 'frame');
    assert.equal(both[1].src, '/api/frames/c1'); assert.equal(both[1].className, 'previous-frame'); assert.equal(both[1].alt, '');
    await tick(700); assert.equal(preview.querySelectorAll('img').length, 1); assert.equal(preview.querySelector('img').src, '/api/frames/c2');
  } else if (scenario === 'activity') {
    ids.mode.value = 'live'; ids.mode.onchange();
    const steps = () => card('transport').querySelector('.steps').textContent;
    ui.event({kind:'transport', type:'step_started'});
    ui.event({kind:'transport', type:'step_progress', message:"En attente d'un navigateur disponible"});
    assert.equal(card('transport').querySelector('.status').dataset.status, 'queued');
    assert.equal(card('transport').querySelector('.status').textContent, 'En file');
    assert.equal(card('transport').dataset.phase, 'queued');
    assert.equal(card('transport').querySelector('.preview').dataset.state, 'queued');
    assert.equal(steps(), 'En attente d’un navigateur disponible');
    ui.event({kind:'transport', type:'step_progress', message:'Ouverture du site'});
    assert.equal(card('transport').querySelector('.status').dataset.status, 'running'); assert.equal(card('transport').dataset.phase, 'working');
    assert.equal(steps(), 'Ouverture du site');
    ui.event({kind:'transport', type:'step_progress', message:'Étape 4'}); assert.ok(steps().startsWith('Étape 4 · '), steps());
    ui.event({kind:'transport', type:'step_progress', message:'Étape 5 {"task":"RAW_PROMPT click"}'}); assert.ok(steps().startsWith('Étape 5 · '));
    ui.event({kind:'transport', type:'step_progress', message:'RAW_TASK: go to page and click submit'}); assert.ok(steps().startsWith('Étape 5 · '));
    ui.event(frame('transport', 'a1', 9)); await loaded(images.at(-1));
    now += 42000; ui.frameMeta('transport'); assert.ok(steps().includes('image il y a 42 s'), steps());
    assert.equal(card('transport').querySelector('.live-badge').textContent, 'AGENT AU TRAVAIL');
    context.__runai.setLanguage('en'); ui.frameMeta('transport'); assert.ok(steps().startsWith('Step 5 · ')); assert.ok(steps().includes('frame 42 s ago'));
    assert.ok(!root.textContent.includes('RAW_'));
  } else if (scenario === 'blocked-summary') {
    await initial(true);
    kinds.forEach(kind => { ui.event({kind, type:'step_started'}); ui.event({kind, type:'step_progress', message:'Navigation sur le site'}); });
    const codes = ['policy_denied', 'no_inventory', 'captcha'];
    kinds.forEach((kind, i) => ui.event({kind, status:'blocked', reason_code:codes[i], summary:'RAW_SUMMARY {"step":1}', error:'RAW_ERROR trace',
      blocked_url_host:'raw-blocked.example', handoff_url:'https://example.org/' + kind}));
    assert.equal(ids.agents.dataset.view, 'summary'); assert.equal(ids.coverage.hidden, false); assert.equal(ids['mission-banner'].hidden, true);
    assert.equal(root.querySelectorAll('.summary-list').length, 1);
    const items = ids.coverage.querySelectorAll('.summary-list li'); assert.equal(items.length, 3);
    assert.ok(items[0].textContent.includes('limite de ce qu’il a le droit'), 'beyond-boundary policy_denied copy');
    assert.ok(items[1].textContent.includes('Plus de disponibilité')); assert.ok(items[2].textContent.includes('vérification humaine'));
    const links = ids.coverage.querySelectorAll('.summary-link'); assert.equal(links.length, 3);
    links.forEach((a, i) => { assert.equal(a.href, 'https://example.org/' + kinds[i]); assert.equal(a.target, '_blank'); assert.ok(a.textContent.includes('Continuer sur example.org')); });
    assert.ok(ids.coverage.textContent.includes('Vos agents vous passent le relais'));
    assert.equal(ids.coverage.querySelectorAll('.chip').length, 3);
    for (const raw of ['RAW_', 'raw-blocked', 'Reprenez la main', '{"']) assert.ok(!root.textContent.includes(raw), raw);
    const before = ids.coverage.children[0]; ui.frameMeta('hotel'); ui.event({kind:'hotel', type:'step_progress', message:'late'});
    assert.equal(ids.coverage.children[0], before, 'Summary is not rebuilt on every poll');
    ids.mode.onchange(); await initial(true);
    kinds.forEach(kind => ui.event({kind, type:'step_started'}));
    ui.event({kind:'registration', status:'blocked', reason_code:'sold_out', handoff_url:'https://example.org/reg'});
    ui.event({kind:'hotel', status:'ready_for_payment', handoff_url:'https://example.org/hotel'});
    ui.event({kind:'transport', status:'failed', reason_code:'provider_error'});
    assert.equal(ids.coverage.dataset.tone, 'partial'); assert.ok(ids.coverage.textContent.includes('1/3 prêt avant paiement'));
    assert.ok(ids.coverage.textContent.includes('Payer sur example.org')); assert.ok(ids.coverage.textContent.includes('Pas de site vérifié'));
  } else if (scenario === 'ready-ctas') {
    await initial(true);
    kinds.forEach(kind => ui.event({kind, type:'step_started'}));
    kinds.forEach(kind => ui.event({kind, status:'ready_for_payment', summary:'RAW total 199 €', handoff_url:'https://example.org/checkout-free/' + kind}));
    assert.equal(ids['mission-banner'].hidden, false); assert.equal(ids['mission-banner'].dataset.tone, 'success');
    assert.ok(ids['mission-banner'].textContent.includes('3/3')); assert.ok(ids['mission-banner'].textContent.includes('Course synthétique'));
    assert.equal(ids.coverage.hidden, true); assert.equal(ids.agents.dataset.view, 'agents');
    const ctas = root.querySelectorAll('.cta'); assert.equal(ctas.length, 3);
    for (const a of ctas) { assert.ok(a.href.startsWith('https://example.org/')); assert.equal(a.target, '_blank'); assert.ok(a.rel.includes('noopener')); assert.ok(a.textContent.includes('à vous de payer sur example.org')); }
    assert.ok(!root.textContent.includes('RAW'));
  } else if (scenario === 'hero') {
    const result = mission(true); result.turns[0].draft = {race: {...race, preparation: {registration: 'unknown', hotel: true, transport: true}}, nights: 2, budget_eur: 450};
    respond('/api/missions', result); await submit('une course');
    let plan = root.querySelector('.plan-card');
    assert.ok(!plan.textContent.includes('—')); assert.ok(plan.querySelector('.route-placeholder')); assert.ok(plan.textContent.includes('Origine à choisir'));
    assert.equal(plan.querySelectorAll('.prep-badge').length, 0); assert.ok(!plan.textContent.includes('✓'));
    const next = mission(true); next.turns[0].draft = {race: {...race, date_status: 'unverified', preparation: {registration: 'covered', hotel: true, transport: true}}, origin_city: 'Paris'};
    respond('/api/missions/m1/messages', next); await submit('ok');
    plan = root.querySelectorAll('.plan-card').at(-1);
    assert.ok(!plan.textContent.includes('✓')); assert.equal(plan.querySelectorAll('.access-warning').length, 1);
    assert.ok(plan.querySelector('.access-warning').textContent.includes('Date pas encore confirmée'));
    assert.ok(plan.textContent.includes('PARIS') || plan.textContent.includes('Paris'));
    const ok = mission(true); ok.turns[0].draft = {race: {...race, preparation: {registration: 'covered', hotel: true, transport: false}}, origin_city: 'Paris'};
    respond('/api/missions/m1/messages', ok); await submit('ok');
    plan = root.querySelectorAll('.plan-card').at(-1);
    assert.ok(plan.textContent.includes('Inscription ✓')); assert.ok(plan.textContent.includes('Transport non couvert'));
  } else if (scenario === 'cities') {
    const result = mission(true); result.turns[0].draft = {race: {...race, city: 'Geneva', country: 'Switzerland', country_code: 'CH'}, origin_city: 'Lisbon', nights: 2};
    respond('/api/missions', result); await submit('une course');
    const plan = root.querySelector('.plan-card');
    assert.ok(plan.textContent.includes('Genève')); assert.ok(plan.textContent.includes('Lisbonne')); assert.ok(plan.textContent.includes('Suisse'));
    assert.ok(!plan.textContent.includes('Geneva'));
    const hooks = context.__runai;
    for (const [raw, fr, en] of [['Geneva', 'Genève', 'Geneva'], ['Genève', 'Genève', 'Geneva'], ['Milano', 'Milan', 'Milan'], ['Lisboa', 'Lisbonne', 'Lisbon'], ['Barcelona', 'Barcelone', 'Barcelona'], ['Den Haag', 'La Haye', 'The Hague'], ['Utrecht', 'Utrecht', 'Utrecht']]) {
      hooks.setLanguage('fr'); assert.equal(hooks.cityName(raw), fr); hooks.setLanguage('en'); assert.equal(hooks.cityName(raw), en);
    }
  } else if (scenario === 'flags') {
    const hooks = context.__runai;
    for (const code of ['IT', 'FR', 'DE', 'NL', 'CH', 'ES', 'PT', 'BE']) {
      const flag = hooks.flag({country_code:code});
      assert.equal(flag.tag, 'svg'); assert.equal(flag.dataset.country, code);
      assert.equal(flag.getAttribute('viewBox'), '0 0 24 16');
      assert.equal(flag.getAttribute('aria-label'), code); assert.ok(flag.children.length >= 2);
      assert.equal(flag.textContent, '', 'Never rely on emoji glyphs');
    }
    const fallback = hooks.flag({country_code:'JP'});
    assert.equal(fallback.tag, 'span'); assert.equal(fallback.textContent, 'JP');
    assert.equal(hooks.flag({}), null);
    assert.equal(hooks.flag({country_code:'<svg>'}), null);
  } else if (scenario === 'observed-age') {
    ids.mode.value = 'live'; ids.mode.onchange();
    ui.event({kind:'hotel', type:'step_started'});
    const badge = card('hotel').querySelector('.live-badge');
    for (const [id, observed, expected] of [
      ['old', now - 120000, 'AGENT AU TRAVAIL'], ['edge', now - 15000, 'AGENT AU TRAVAIL'],
      ['fresh', now - 14999, 'EN DIRECT'], ['future', now + 30000, 'AGENT AU TRAVAIL'],
      ['missing', null, 'AGENT AU TRAVAIL']]) {
      ui.event({...frame('hotel',id,1), observed_at: observed === null ? null : new Date(observed).toISOString()});
      await loaded(images.at(-1)); assert.equal(badge.textContent, expected, id);
    }
    ui.event({...frame('hotel','expires',2), observed_at: new Date(now).toISOString()}); await loaded(images.at(-1));
    now += 15000; await tick(15000); assert.equal(badge.textContent, 'AGENT AU TRAVAIL', 'Expires without polling');
  } else if (scenario === 'checkpoints') {
    const hooks = context.__runai;
    for (const lang of ['fr', 'en']) {
      hooks.setLanguage(lang);
      for (const code of ['checkpoint_unverified', 'checkpoint_reached']) {
        ui.event({kind:'hotel', type:'step_started'});
        ui.event({kind:'hotel', type:'step_progress', message:'Essai d’un autre site'});
        ui.event({kind:'hotel', status:'blocked', reason_code:code, checkpoint_reached:true,
          summary:'{"task":"RAW_TASK","blocked_url_host":"PRIVATE_HOST"}', handoff_url:'https://example.org/hotel'});
        const copy = card('hotel').querySelector('.steps').textContent;
        assert.ok(copy.includes(lang === 'fr' ? 'Étape de réservation atteinte — à vérifier' : 'Booking step reached — please verify'));
        assert.ok(!/indisponible|unavailable/.test(copy));
        assert.ok(card('hotel').querySelector('.handoff').textContent.includes(lang === 'fr' ? 'Continuer sur example.org' : 'Continue on example.org'));
        assert.equal(card('hotel').dataset.status, 'blocked', 'Never upgrade an unverified checkpoint');
      }
      assert.ok(!hooks.reason(null, 'failed').includes('indisponible'));
    }
    for (const status of ['ready_for_payment', 'blocked', 'failed', 'cancelled']) {
      ui.event({kind:'transport', type:'step_progress', message:'Essai d’un autre site'});
      ui.event({kind:'transport', status, reason_code:'captcha', summary:'RAW_TASK JSON blocked_url_host', handoff_url:'https://example.org/transport'});
      ui.frameMeta('transport');
      assert.ok(!/Essai|Trying/.test(card('transport').textContent));
      ui.event({kind:'transport', type:'step_progress', message:'Essai d’un autre site'});
      assert.ok(!/Essai|Trying/.test(card('transport').textContent), 'Late progress cannot replace terminal copy');
    }
    for (const raw of ['RAW_TASK', 'PRIVATE_HOST', 'blocked_url_host', '{"task"']) assert.ok(!root.textContent.includes(raw));
  } else if (scenario === 'opening') {
    kinds.forEach(kind => ui.event({kind, type:'step_started'}));
    for (const kind of kinds) {
      assert.equal(card(kind).querySelector('.preview').dataset.state, 'starting');
      assert.ok(card(kind).querySelector('.waiting-copy').textContent.includes('Ouverture du site'));
      assert.ok(card(kind).querySelector('.browser-skeleton'));
      assert.equal(card(kind).querySelector('.live-badge').hidden, true);
    }
  } else if (scenario === 'focus') {
    ids.agents.hidden = false; const hooks = context.__runai;
    kinds.forEach(kind => ui.event({kind, type:'step_started'}));
    assert.equal(hooks.focus('hotel'), 'hotel'); assert.equal(ids.agents.dataset.focus, 'hotel');
    assert.equal(card('hotel').dataset.focused, 'true'); assert.equal(card('transport').dataset.focused, 'false');
    const button = card('hotel').querySelector('.focus-toggle'); assert.equal(button.getAttribute('aria-pressed'), 'true');
    button.onclick({stopPropagation() {}}); assert.equal(ids.agents.dataset.focus, undefined); assert.equal(button.getAttribute('aria-pressed'), 'false');
    card('transport').querySelector('.focus-toggle').onclick({}); assert.equal(ids.agents.dataset.focus, 'transport');
    listeners.keydown({key: 'ArrowRight'}); assert.equal(ids.agents.dataset.focus, 'registration');
    listeners.keydown({key: 'ArrowLeft'}); assert.equal(ids.agents.dataset.focus, 'transport');
    listeners.keydown({key: 'Escape'}); assert.equal(ids.agents.dataset.focus, undefined);
    hooks.focus('hotel'); ids.mode.onchange(); assert.equal(ids.agents.dataset.focus, undefined);
  }
  assert.equal(responses.length, 0, 'Consume expected responses');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


@pytest.mark.parametrize("scenario", [
    "chronology", "uncertain", "english", "pending", "background", "sync", "retry", "sensitive", "empty",
    "generation", "frames", "stale", "decode", "replay", "launch", "disconnect", "polish",
    "snapshot-error", "welcome", "fr-detect", "fresh", "never-started", "coverage", "success", "preparation",
    "crossfade", "activity", "blocked-summary", "ready-ctas", "hero", "cities", "focus",
    "flags", "observed-age", "checkpoints", "opening",
])
def test_executable_browser_states(scenario):
    result = subprocess.run(
        ["node", "-e", DOM_HARNESS],
        input=json.dumps({"source": JS, "scenario": scenario}),
        text=True, capture_output=True, check=False, timeout=15,
    )
    assert result.returncode == 0, result.stderr
