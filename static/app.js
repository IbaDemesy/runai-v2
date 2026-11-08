(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const kinds = ['registration', 'hotel', 'transport'];
  const terminal = new Set(['ready_for_payment', 'blocked', 'failed', 'cancelled']);
  const labels = {pending: 'En attente', running: 'En action', ready_for_payment: 'À vous de jouer', blocked: 'À reprendre', failed: 'Interrompu', cancelled: 'Arrêté'};
  let mission = null, after = 0, timer = null, busy = false, generation = 0, liveReady = null;
  let backgroundSupported = true;
  const agentState = {};
  const redact = value => String(value ?? '')
    .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, '[contact masqué]')
    .replace(/\b(?:\d[ -]?){13,19}\b/g, '[carte masquée]')
    .replace(/(?:\+\d[\d ().-]{7,}\d|\b0\d(?:[ .-]?\d){8}\b)/g, '[téléphone masqué]')
    .replace(/\b(?:sk-|hapi_|hai_)[a-z0-9_-]{8,}\b/gi, '[clé masquée]')
    .replace(/\b(?:bearer\s+\S+|(?:password|passwd|mot de passe|token|api[_ -]?key|secret|cvv|cvc)\s*[:=]\s*\S+)/gi, '[identifiant masqué]');
  const node = (tag, cls, value) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (value !== undefined) el.textContent = redact(value);
    return el;
  };
  const safeURL = value => {
    if (typeof value !== 'string') return null;
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || /(^|\.)hcompany\.ai$|(^|\.)h\.ai$/.test(url.hostname) ||
          /(?:share\/api|trajector|session|token|secret|auth|api[_-]?key)/i.test(url.href) ||
          url.hash || /@|%40/i.test(url.pathname) || [...url.searchParams].some(([key, value]) =>
            /token|session|sid|auth|key|signature|email|phone|password/i.test(key) ||
            /@|(?:\d[ -]?){13,19}/.test(value))) return null;
      return url.href;
    } catch { return null; }
  };
  function link(url, title, cls) {
    const href = safeURL(url);
    if (!href) return null;
    const a = node('a', cls, title);
    Object.assign(a, {href, target: '_blank', rel: 'noopener noreferrer', referrerPolicy: 'no-referrer'});
    return a;
  }
  function normalize(raw) {
    const envelope = raw?.mission || raw || {};
    const data = envelope.turns?.at(-1) || raw?.turn || envelope;
    const plan = data.draft || data.plan || envelope.trip;
    return {...data, id: envelope.id || data.mission_id || data.id,
      assistant_message: typeof data.message === 'string' ? data.message : '',
      question: typeof data.question === 'string' ? data.question : '',
      suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
      candidates: Array.isArray(data.candidates) ? data.candidates : [],
      plan: plan?.race?.name ? plan : null,
      ready_to_confirm: data.ready_to_confirm === true || data.confirmation_required === true};
  }
  const locale = () => mission?.lang === 'en' ? 'en-GB' : 'fr-FR';
  const date = value => {
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Date à confirmer';
    return new Intl.DateTimeFormat(locale(), {day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC'}).format(new Date(value));
  };
  const distance = race => Number.isFinite(race.distance_km)
    ? `${new Intl.NumberFormat(locale(), {maximumFractionDigits: 1}).format(race.distance_km)} km`
    : race.distance_label || 'Distance à confirmer';
  function scroll() { $('thread').scrollTop = $('thread').scrollHeight; }
  function badge() {
    $('mode-badge').textContent = {demo: 'SIMULATION SYNTHÉTIQUE', replay: 'REPLAY · enregistrement synthétique · heure originale', live: 'LIVE · agents réels · arrêt avant paiement'}[$('mode').value];
    $('live-hint').hidden = !($('mode').value === 'live' && liveReady && (!liveReady.linkup || !liveReady.h));
    document.querySelector('.agent-footnote').hidden = $('mode').value === 'live';
  }
  const errorCopy = status => status === 501 ? 'Ce service n’est pas disponible dans ce mode. Aucun résultat n’a été simulé.'
    : status === 409 ? 'Le plan a changé. Vérifiez la dernière proposition avant de continuer.'
    : status === 422 ? 'Ce choix n’a pas pu être pris en compte. Essayez une autre réponse.'
    : status === 404 ? 'Cette session n’est plus disponible. Changez de mode pour recommencer.'
    : 'La connexion a été interrompue. Votre dernière étape est conservée.';
  function error(err, retry) {
    $('toast').querySelectorAll('.retry').forEach(el => el.remove()); $('toast').hidden = false;
    $('toast').querySelector('p').textContent = errorCopy(err.status);
    if (retry) {
      const button = node('button', 'retry', 'Réessayer ↗');
      button.onclick = () => { $('toast').hidden = true; retry(); }; $('toast').append(button);
    }
  }
  async function api(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 150000);
    try {
      const response = await fetch(path, {signal: controller.signal, ...(body === undefined ? {} : {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})});
      if (!response.ok) throw Object.assign(new Error('Request failed'), {status: response.status});
      return await response.json();
    } finally { clearTimeout(timeout); }
  }
  async function guideRequest(path, body) {
    try { return await api(path, {...body, ...(backgroundSupported ? {background: true} : {})}); }
    catch (err) {
      // Older synchronous servers reject the additive field before running discovery.
      if (err.status !== 422 || !backgroundSupported) throw err;
      backgroundSupported = false; return api(path, body);
    }
  }
  function message(role, content) {
    $('welcome').hidden = true;
    const wrap = node('article', `message ${role}`);
    if (role === 'assistant') wrap.append(node('span', 'avatar', 'R↗'));
    const inner = node('div', 'message-content');
    if (role === 'assistant') inner.append(node('div', 'message-name', 'RUNAI · VOTRE COPILOTE'));
    const bubble = node('p', 'bubble', content);
    inner.append(bubble); wrap.append(inner); $('thread').append(wrap); scroll();
    return {wrap, inner, bubble};
  }
  function sources(race) {
    const row = node('div', 'sources');
    if (race.synthetic) row.append(node('span', 'provenance', 'Synthétique'));
    for (const source of [...new Set(race.source_urls || [])].slice(0, 2)) {
      const href = safeURL(source); if (!href) continue;
      row.append(link(href, `${new URL(href).hostname.replace(/^www\./, '')} ↗`, 'source-badge'));
    }
    const official = link(race.official_url, 'Site officiel ↗', 'source-badge');
    if (official && !row.children.length) row.append(official);
    if (race.retrieved_at && Number.isFinite(Date.parse(race.retrieved_at))) {
      const time = node('time', 'retrieved', `Vérifié le ${new Intl.DateTimeFormat(locale(), {day: 'numeric', month: 'short', timeZone: 'UTC'}).format(new Date(race.retrieved_at))}`);
      time.dateTime = race.retrieved_at; row.append(time);
    }
    return row;
  }
  function accessWarning(race) {
    const access = race.registration_access;
    if (!access) return null;
    const copy = [access.account_required === true ? 'Compte requis : reprise manuelle avant sa création.' : null,
      access.captcha === true ? 'Vérification humaine possible.' : null,
      access.account_required == null ? 'Accès à l’inscription non vérifié.' : null].filter(Boolean).join(' ');
    return copy ? node('p', 'access-warning', copy) : null;
  }
  function candidates(items) {
    const grid = node('div', 'candidates');
    for (const race of items) {
      const card = node('article', 'candidate');
      card.append(node('div', 'distance', distance(race)), node('h3', '', race.name || 'Course proposée'),
        node('p', 'location', [race.city, race.country].filter(Boolean).join(' · ')),
        node('p', 'race-date', date(race.race_date)),
        node('span', 'date-status', race.date_status === 'official' ? 'Date officielle' : 'Date à confirmer'), sources(race));
      const warning = accessWarning(race); if (warning) card.append(warning); grid.append(card);
    }
    return grid;
  }
  function planCard(p, ready) {
    const card = node('section', 'plan-card'), head = node('div', 'plan-head');
    head.append(node('p', 'eyebrow', 'VOTRE LIGNE DE DÉPART'), node('h3', '', p.race.name),
      node('p', 'location', `${[p.race.city, p.race.country].filter(Boolean).join(' · ')} · ${distance(p.race)}`), sources(p.race));
    const facts = node('dl', 'plan-facts');
    for (const [label, value] of [['Course', date(p.race.race_date)], ['Arrivée', p.arrival_date && date(p.arrival_date)],
      ['Retour', p.departure_date && date(p.departure_date)], ['Départ', p.origin_city], ['Nuits', p.nights], ['Budget', p.budget_eur != null ? `${p.budget_eur} €` : null]]) {
      if (value == null) continue;
      const f = node('div', 'fact'); f.append(node('dt', '', label), node('dd', '', value)); facts.append(f);
    }
    card.append(head, facts, node('p', 'plan-note', 'Départ, nuits et budget : préférences modifiables, pas des disponibilités réservées.'));
    const warning = accessWarning(p.race); if (warning) card.append(warning);
    const site = link(p.race.registration_url || p.race.official_url, 'Voir l’inscription officielle ↗', 'site-link'); if (site) card.append(site);
    if (ready) {
      const area = node('div', 'confirm-area'), button = node('button', 'confirm', 'Confirmer le plan et lancer les 3 agents ↗');
      button.type = 'button'; button.onclick = () => confirm(button);
      area.append(node('p', '', 'Aucun achat, compte, consentement ou engagement. Vous gardez la main.'), button); card.append(area);
    }
    return card;
  }
  function renderTurn(raw, reply) {
    const turn = normalize(raw); if (!turn.id) throw Error('Incomplete response');
    mission = {...mission, ...turn};
    reply.inner.querySelectorAll('.pending').forEach(el => el.remove());
    reply.bubble.textContent = redact(turn.assistant_message || 'Aucune proposition pour le moment. Essayons une autre envie de course.');
    if (turn.candidates.length) reply.inner.append(candidates(turn.candidates));
    if (turn.plan) reply.inner.append(planCard(turn.plan, turn.ready_to_confirm));
    if (turn.question) reply.inner.append(node('p', 'question', turn.question));
    const chips = node('div', 'chips'); chips.dataset.testid = 'chips';
    for (const suggestion of turn.suggestions) {
      if (!suggestion.id || !suggestion.label || suggestion.kind === 'confirm') continue;
      const item = node('div', 'suggestion'), button = node('button', 'chip', `${suggestion.label} ↗`);
      button.type = 'button'; button.onclick = () => send({suggestion_id: suggestion.id}, suggestion.label);
      item.append(button, node('span', 'suggestion-meta', {source: 'Course sourcée', synthetic: 'Exemple synthétique', suggested_default: 'Suggestion · modifiable'}[suggestion.provenance] || 'Choisir cette réponse')); chips.append(item);
    }
    if (chips.children.length) reply.inner.append(chips); scroll();
  }
  function loading(value) {
    busy = value; $('send').disabled = value; $('send').textContent = value ? '···' : '↑';
    document.querySelectorAll('.chip,.example-chips button,.confirm').forEach(b => { b.disabled = value || b.dataset.retired === 'true'; });
  }
  function pending(reply, started) {
    reply.bubble.textContent = 'Je recherche les courses et leurs dates officielles. Vous n’avez pas besoin de connaître la date.';
    const box = node('div', 'pending'), progress = node('p', 'pending-copy', 'Recherche en cours · quelques instants…');
    const skeletons = node('div', 'skeletons'); skeletons.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 2; i++) { const card = node('div', 'skeleton'); card.append(node('span'), node('span'), node('span')); skeletons.append(card); }
    box.append(progress, skeletons); reply.inner.append(box); scroll();
    let clock;
    const tick = () => {
      const elapsed = Math.floor((Date.now() - started) / 1000);
      progress.textContent = `Recherche en cours · ${elapsed} s écoulées${elapsed >= 20 ? ' · les sources officielles peuvent prendre un peu de temps.' : ''}`;
      clock = setTimeout(tick, 1000);
    };
    clock = setTimeout(tick, 1000); return () => clearTimeout(clock);
  }
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function send(body, label, attempt = null) {
    if (busy) return;
    const token = generation; loading(true); $('toast').hidden = true;
    const previousControls = document.querySelectorAll('.chips,.confirm-area');
    if (!attempt) { message('user', label); $('message').value = ''; $('message').style.height = ''; attempt = {reply: message('assistant', ''), id: null}; }
    const reply = attempt.reply; reply.inner.querySelectorAll('.pending').forEach(el => el.remove());
    const started = Date.now(), stop = pending(reply, started);
    try {
      let result;
      if (attempt.id && !attempt.failed) result = await api(`/api/missions/${encodeURIComponent(attempt.id)}`);
      else result = await guideRequest(attempt.id || mission ? `/api/missions/${encodeURIComponent(attempt.id || mission.id)}/messages` : '/api/missions', mission || attempt.id ? body : {...body, mode: $('mode').value});
      if (token !== generation) return;
      attempt.id = (result.mission || result).id; attempt.failed = false;
      while ((result.mission || result).status === 'discovering') {
        if (Date.now() - started > 150000) throw Error('Discovery timeout');
        await delay(800); if (token !== generation) return;
        result = await api(`/api/missions/${encodeURIComponent(attempt.id)}`); if (token !== generation) return;
      }
      const envelope = result.mission || result;
      if (envelope.error) { attempt.failed = true; throw Error('Discovery failed'); }
      renderTurn(result, reply);
      previousControls.forEach(control => control.querySelectorAll('button').forEach(button => { button.disabled = true; button.dataset.retired = 'true'; }));
    } catch (err) {
      if (token !== generation) return;
      reply.inner.querySelectorAll('.pending').forEach(el => el.remove());
      reply.bubble.textContent = 'La recherche n’a pas abouti. Réessayez : votre demande est conservée.';
      error(err, () => send(body, label, attempt));
    } finally { stop(); if (token === generation) { loading(false); scroll(); } }
  }
  async function confirm(button) {
    if (busy || !mission?.ready_to_confirm) return;
    const token = generation; loading(true); button.textContent = 'Lancement…';
    try {
      const result = await api(`/api/missions/${encodeURIComponent(mission.id)}/confirm`, {confirmed: true});
      if (token !== generation) return;
      mission.ready_to_confirm = false; document.querySelectorAll('.confirm-area,.chips').forEach(el => el.remove());
      $('agents').hidden = false; $('workspace').classList.add('executing');
      $('history-toggle').hidden = false; $('history-toggle').setAttribute('aria-expanded', 'false');
      consume(result); poll(token);
    } catch (err) { if (token === generation) { error(err); button.textContent = 'Réessayer la confirmation'; } }
    finally { if (token === generation) loading(false); }
  }
  const cardFor = kind => document.querySelector(`[data-agent="${kind}"]`);
  function frameMeta(kind) {
    const state = agentState[kind], card = cardFor(kind); if (!state) return;
    const stale = state.stale || (state.received && Date.now() - state.received > 20000 && !terminal.has(state.status));
    const mode = $('mode').value;
    const status = state.image ? stale ? 'Image conservée · suivi interrompu' : terminal.has(state.status) ? 'Dernière capture · agent arrêté' : mode === 'live' ? 'Capture en direct' : 'Capture synthétique' : 'Capture indisponible';
    card.querySelector('.preview').dataset.state = state.image ? stale ? 'stale' : 'available' : 'unavailable';
    const time = state.image ? (mode === 'replay' ? state.recorded : state.observed) : null;
    card.querySelector('.frame-meta').textContent = `${status}${time && Number.isFinite(Date.parse(time)) ? ` · ${mode === 'replay' ? 'heure originale' : 'observée'} ${new Intl.DateTimeFormat(locale(), {hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC'}).format(new Date(time))} UTC` : state.image ? ' · heure indisponible' : ''}`;
  }
  function loadFrame(kind, e) {
    if (typeof e.frame_id !== 'string' || !/^[a-zA-Z0-9_-]{1,160}$/.test(e.frame_id)) return;
    const state = agentState[kind], token = generation;
    if (state.requested === e.frame_id) return;
    state.requested = e.frame_id;
    const version = state.version = (state.version || 0) + 1;
    const img = new Image(); img.alt = `${$('mode').value === 'live' ? 'Navigateur de l’agent' : 'Navigateur synthétique'} · ${kind}`; img.referrerPolicy = 'no-referrer';
    const current = () => token === generation && agentState[kind] === state && version === state.version;
    const fail = () => { if (current()) { state.stale = true; frameMeta(kind); } };
    img.onerror = fail;
    img.onload = async () => {
      try {
        if (img.decode) await img.decode(); if (!current()) return;
        state.image = img; state.stale = false; state.received = Date.now(); state.observed = e.observed_at; state.recorded = e.recorded_at;
        cardFor(kind).querySelector('.preview').replaceChildren(img); frameMeta(kind);
      } catch { fail(); }
    };
    img.src = `/api/frames/${encodeURIComponent(e.frame_id)}`;
  }
  function event(raw) {
    const e = {...raw, ...raw.data}; if (Number.isFinite(Number(e.sequence))) after = Math.max(after, Number(e.sequence));
    if (!kinds.includes(e.kind)) return;
    const state = agentState[e.kind] ||= {status: 'pending'}, card = cardFor(e.kind);
    if (terminal.has(e.status)) state.status = e.status;
    else if (e.type === 'step_started' && !terminal.has(state.status)) state.status = 'running';
    const pill = card.querySelector('.status'); pill.dataset.status = state.status; pill.textContent = labels[state.status] || labels.pending;
    const copy = {pending: 'L’agent se prépare.', running: {registration: 'L’agent vérifie le parcours d’inscription.', hotel: 'L’agent explore les hébergements pour votre séjour.', transport: 'L’agent recherche votre trajet aller-retour.'}[e.kind],
      ready_for_payment: 'Préparation terminée. Reprenez sur le site, sans paiement effectué.', blocked: 'Une étape nécessite votre intervention. Aucun engagement effectué.', failed: 'La préparation a été interrompue. Aucun engagement effectué.', cancelled: 'L’agent est arrêté. Aucun engagement effectué.'};
    card.querySelector('.steps').textContent = copy[state.status] || copy.pending;
    if (e.type === 'live_frame' && e.frame_id) loadFrame(e.kind, e);
    const handoff = link(e.handoff_url, 'Reprendre sur le site ↗', 'handoff-link'); if (handoff) card.querySelector('.handoff').replaceChildren(handoff);
    frameMeta(e.kind);
  }
  function consume(raw) {
    const envelope = raw.mission || raw, events = Array.isArray(envelope) ? envelope : envelope.events || [];
    for (const e of [...events].sort((a,b) => (a.sequence || 0) - (b.sequence || 0))) if (!e.sequence || Number(e.sequence) > after) event(e);
    for (const result of envelope.results || []) event(result);
    return kinds.every(kind => terminal.has(agentState[kind]?.status));
  }
  async function poll(token) {
    if (token !== generation) return;
    try {
      const events = await api(`/api/missions/${encodeURIComponent(mission.id)}/events?after=${after}`);
      if (token !== generation) return; consume(events);
      const snapshot = await api(`/api/missions/${encodeURIComponent(mission.id)}`); if (token !== generation) return;
      const finished = consume(snapshot); kinds.forEach(frameMeta);
      if (!finished) timer = setTimeout(() => poll(token), 1000);
    } catch (err) {
      if (token !== generation) return;
      kinds.forEach(kind => { const state = agentState[kind]; if (state) { state.stale = true; frameMeta(kind); } });
      error(err, () => poll(token));
    }
  }
  $('composer').onsubmit = e => { e.preventDefault(); const value = $('message').value.trim(); if (value) send({text: value}, value); };
  $('message').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('composer').requestSubmit(); } };
  $('message').oninput = () => { $('message').style.height = 'auto'; $('message').style.height = `${Math.min($('message').scrollHeight, 130)}px`; };
  document.querySelectorAll('[data-prompt]').forEach(button => { button.onclick = () => send({text: button.dataset.prompt}, button.dataset.prompt); });
  $('history-toggle').onclick = () => {
    const expanded = $('history-toggle').getAttribute('aria-expanded') !== 'true'; $('history-toggle').setAttribute('aria-expanded', String(expanded));
    $('workspace').classList[expanded ? 'add' : 'remove']('history-open'); $('history-toggle').textContent = expanded ? 'Masquer la conversation ↑' : 'Voir le plan et la conversation ↓';
  };
  $('toast').querySelector('button').onclick = () => { $('toast').hidden = true; };
  $('mode').onchange = () => {
    generation++; clearTimeout(timer); mission = null; after = 0; loading(false);
    for (const kind of kinds) delete agentState[kind];
    document.querySelectorAll('.message').forEach(el => el.remove());
    document.querySelectorAll('.agent').forEach(card => {
      card.querySelector('.preview').textContent = 'En attente de la première capture'; card.querySelector('.preview').dataset.state = 'unavailable';
      card.querySelector('.frame-meta').textContent = 'Aucune image reçue'; card.querySelector('.steps').textContent = 'L’agent se prépare.'; card.querySelector('.handoff').replaceChildren();
      const pill = card.querySelector('.status'); pill.dataset.status = 'pending'; pill.textContent = labels.pending;
    });
    $('welcome').hidden = false; $('agents').hidden = true; $('history-toggle').hidden = true;
    $('workspace').classList.remove('executing'); $('workspace').classList.remove('history-open'); $('message').value = ''; $('toast').hidden = true; badge();
  };
  badge(); const initialGeneration = generation;
  api('/api/health').then(health => {
    liveReady = health.live_ready || null;
    if (generation === initialGeneration && !mission && !busy && ['demo', 'replay', 'live'].includes(health.mode)) $('mode').value = health.mode;
    badge();
  }).catch(() => {});
})();
