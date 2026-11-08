(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const kinds = ['registration', 'hotel', 'transport'];
  const terminal = new Set(['ready_for_payment', 'blocked', 'failed', 'cancelled']);
  const labels = {pending: 'En attente', running: 'En action', ready_for_payment: 'À vous de jouer', blocked: 'À reprendre', failed: 'Interrompu', cancelled: 'Arrêté'};
  let mission = null, after = 0, timer = null, busy = false, generation = 0, liveReady = null;
  let backgroundSupported = true, language = globalThis.navigator?.language?.startsWith('en') ? 'en' : 'fr';
  const t = (fr, en) => language === 'en' ? en : fr;
  const translations = {
    'ENVIRONNEMENT': 'ENVIRONMENT', 'Démo': 'Demo', 'Aucun achat. Aucune réservation. Vous gardez la main.': 'No purchase. No booking. You stay in control.',
    'Live indisponible : configuration des services incomplète.': 'Live unavailable: service setup is incomplete.',
    'VOTRE PROCHAINE LIGNE DE DÉPART': 'YOUR NEXT STARTING LINE', 'Vous courez.': 'You run.', 'On prépare': 'We handle', 'le reste.': 'the rest.',
    'Une envie de course ? Trouvons votre dossard, votre hôtel et votre trajet. Un plan clair, puis trois agents à vos côtés.': 'A race in mind? Let’s find your bib, hotel and journey. One clear plan, then three agents on your side.',
    'Un marathon au printemps en Italie': 'A spring marathon in Italy', 'Un trail en Suisse cet été': 'A summer trail in Switzerland', 'Le semi de Lisbonne': 'The Lisbon half marathon',
    'La course': 'The race', 'Le plan': 'The plan', 'Le départ': 'The start', 'Votre message': 'Your message', 'Quelle course vous fait envie ?': 'What race inspires you?',
    'Envoyer le message': 'Send message', 'Les trois agents': 'The three agents', 'À votre rythme. Les agents s’arrêtent avant tout paiement ou engagement.': 'At your pace. Agents stop before any payment or commitment.',
    'VOTRE ÉQUIPE EN ACTION': 'YOUR TEAM IN ACTION', 'Trois agents. Un départ.': 'Three agents. One start.', 'Préparation en parallèle · arrêt avant paiement': 'Parallel preparation · stopping before payment',
    'Inscription / dossard': 'Bib', 'Dossard': 'Bib', 'Hôtel': 'Hotel', 'En attente': 'Pending', 'En action': 'Working', 'À vous de jouer': 'Over to you', 'À reprendre': 'Needs your help', 'Interrompu': 'Interrupted', 'Arrêté': 'Stopped',
    'En attente de la première capture': 'Waiting for the first screenshot', 'Aucune image reçue': 'No image received', 'L’agent se prépare.': 'The agent is getting ready.',
    'Démo et replay : illustrations synthétiques, aucun panier réel préparé.': 'Demo and replay: synthetic illustrations, no real checkout prepared.', 'Impossible de continuer': 'Unable to continue', 'Fermer la notification': 'Close notification',
    'RUNAI · VOTRE COPILOTE': 'RUNAI · YOUR COPILOT', 'Date à confirmer': 'Date to confirm', 'Distance à confirmer': 'Distance to confirm', 'Synthétique': 'Synthetic', 'Site officiel ↗': 'Official site ↗',
    'Compte requis : reprise manuelle avant sa création.': 'Account required: continue manually before creating it.', 'Vérification humaine possible.': 'Human verification may be required.', 'Accès à l’inscription non vérifié.': 'Registration to check.',
    'Course proposée': 'Suggested race', 'Date officielle': 'Official date', 'VOTRE LIGNE DE DÉPART': 'YOUR STARTING LINE', 'Course': 'Race', 'Arrivée': 'Arrival', 'Retour': 'Return', 'Départ': 'Origin', 'Nuits': 'Nights', 'Budget': 'Budget',
    'Départ, nuits et budget : préférences modifiables, pas des disponibilités réservées.': 'Origin, nights and budget: editable preferences, not reserved availability.', 'Voir l’inscription officielle ↗': 'View official registration ↗',
    'Confirmer le plan et lancer les 3 agents ↗': 'Confirm plan and launch 3 agents ↗', 'Aucun achat, compte, consentement ou engagement. Vous gardez la main.': 'No purchase, account, consent or commitment. You stay in control.',
    'Course sourcée': 'Sourced race', 'Exemple synthétique': 'Synthetic example', 'Suggestion · modifiable': 'Suggestion · editable', 'Choisir cette réponse': 'Choose this answer',
    'Je recherche les courses et leurs dates officielles. Vous n’avez pas besoin de connaître la date.': 'I’m finding races and their official dates. You don’t need to know the date.', 'Recherche en cours · quelques instants…': 'Searching · just a moment…',
    'La recherche n’a pas abouti. Réessayez : votre demande est conservée.': 'The search did not finish. Try again: your request is saved.', 'Lancement…': 'Launching…', 'Réessayer la confirmation': 'Retry confirmation', 'Réessayer ↗': 'Retry ↗',
    'Masquer la conversation ↑': 'Hide conversation ↑', 'Voir le plan et la conversation ↓': 'View plan and conversation ↓',
    'Ce service n’est pas disponible dans ce mode. Aucun résultat n’a été simulé.': 'This service is unavailable in this mode. No result was simulated.', 'Le plan a changé. Vérifiez la dernière proposition avant de continuer.': 'The plan changed. Check the latest proposal before continuing.',
    'Ce choix n’a pas pu être pris en compte. Essayez une autre réponse.': 'This choice could not be applied. Try another answer.', 'Cette session n’est plus disponible. Changez de mode pour recommencer.': 'This session is unavailable. Change mode to start again.', 'La connexion a été interrompue. Votre dernière étape est conservée.': 'Connection interrupted. Your last step is saved.'
  };
  const translate = value => {
    const raw = String(value ?? ''), key = raw.replace(/\s+/g, ' ').trim();
    return language === 'en' ? translations[key] || raw : raw;
  };
  const staticText = new WeakMap();
  function localize() {
    if (!document.body) return;
    document.documentElement.lang = language;
    document.title = t('RunAI — votre prochaine ligne de départ', 'RunAI — your next starting line');
    const walk = element => {
      for (const child of element.childNodes) {
        if (child.nodeType === 3) {
          if (!staticText.has(child)) staticText.set(child, child.textContent);
          child.textContent = translate(staticText.get(child));
        } else if (child.nodeType === 1) walk(child);
      }
      for (const attr of ['placeholder', 'aria-label']) if (element.hasAttribute(attr)) {
        const key = `i18n-${attr}`;
        if (!element.hasAttribute(`data-${key}`)) element.setAttribute(`data-${key}`, element.getAttribute(attr));
        element.setAttribute(attr, translate(element.getAttribute(`data-${key}`)));
      }
    };
    walk(document.body);
  }
  const clean = value => String(value ?? '').replace(/\s*[—–-]?\s*(?:accès inconnu|access unknown)/gi, '');
  const reasons = {
    no_site_coverage: ['Aucun site compatible pour cette étape.', 'No supported site for this step.'],
    policy_denied: ['Ce site ne permet pas cette préparation.', 'This site does not permit this preparation.'],
    date_mismatch: ['Les dates ne correspondent pas au séjour.', 'The dates do not match your trip.'],
    no_inventory: ['Aucune disponibilité pour ces dates.', 'No availability for these dates.'],
    sold_out: ['Cette offre est complète.', 'This offer is sold out.'],
    registration_closed: ['Les inscriptions sont fermées.', 'Registration is closed.'],
    login_required: ['Une connexion est nécessaire : à vous de jouer.', 'Sign-in is required: over to you.'],
    captcha: ['Une vérification humaine est nécessaire.', 'Human verification is required.'],
    consent_required: ['Votre consentement est nécessaire.', 'Your consent is required.'],
    unreviewed_redirect: ['Le nouveau site reste à vérifier.', 'The new site needs review.'],
    over_budget: ['Cette offre dépasse votre budget.', 'This offer exceeds your budget.'],
    step_limit: ['La préparation a atteint sa limite.', 'Preparation reached its step limit.'],
    session_failed: ['La session du navigateur a été interrompue.', 'The browser session was interrupted.'],
    timeout: ['Le site a pris trop de temps à répondre.', 'The site took too long to respond.'],
    unsafe_claim: ['Le résultat ne peut pas être vérifié en sécurité.', 'The result cannot be safely verified.'],
    provider_error: ['Le service est momentanément indisponible.', 'The service is temporarily unavailable.']
  };
  const reason = (code, status) => reasons[code]?.[language === 'en' ? 1 : 0] || ({
    blocked: t('Une étape nécessite votre intervention.', 'This step needs your help.'),
    failed: t('La préparation a été interrompue.', 'Preparation was interrupted.'),
    cancelled: t('L’agent est arrêté.', 'The agent was stopped.')
  }[status] || t('L’agent se prépare.', 'The agent is getting ready.'));
  const flag = race => /^[a-z]{2}$/i.test(race.country_code || race.country || '')
    ? [...(race.country_code || race.country).toUpperCase()].map(c => String.fromCodePoint(127397 + c.charCodeAt())).join('') : '';
  const countdown = race => {
    const days = Math.ceil((Date.parse(race.race_date) - Date.now()) / 86400000);
    return Number.isFinite(days) && days >= 0 ? t(`J−${days}`, `${days} days to go`) : '';
  };
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
    if (value !== undefined) el.textContent = redact(translate(clean(value)));
    return el;
  };
  const safeURL = value => {
    if (typeof value !== 'string') return null;
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || url.username || url.password || /(^|\.)hcompany\.ai$|(^|\.)h\.ai$/.test(url.hostname) ||
          /(?:share\/api|trajector|session|token|secret|auth|api[_-]?key)/i.test(url.href) ||
          url.hash || /@|%40/i.test(url.pathname) || [...url.searchParams].some(([key, value]) =>
            /token|session|sid|auth|key|signature|email|phone|password|booking|reservation|checkout|cart|order|passenger|customer/i.test(key) ||
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
      language: envelope.language,
      plan: plan?.race?.name ? plan : null,
      ready_to_confirm: data.ready_to_confirm === true || data.confirmation_required === true};
  }
  const locale = () => language === 'en' ? 'en-GB' : 'fr-FR';
  function detectLanguage(value) {
    if (/\b(which|where|how many|what budget|here's|would you|i want|i would|i'd like|let's|your trip)\b/i.test(value)) language = 'en';
    else if (/\b(laquelle|combien|quel|quelle|tu pars|je veux|je voudrais|voilà|ton séjour)\b/i.test(value)) language = 'fr';
  }
  const date = value => {
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return t('Date à confirmer', 'Date to confirm');
    return new Intl.DateTimeFormat(locale(), {day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC'}).format(new Date(value));
  };
  const distance = race => Number.isFinite(race.distance_km)
    ? `${new Intl.NumberFormat(locale(), {maximumFractionDigits: 1}).format(race.distance_km)} km`
    : race.distance_label || 'Distance à confirmer';
  function scroll() { $('thread').scrollTop = $('thread').scrollHeight; }
  function badge() {
    $('mode-badge').textContent = {demo: t('SIMULATION SYNTHÉTIQUE', 'SYNTHETIC DEMO'), replay: t('REPLAY · SYNTHÉTIQUE · heure originale', 'REPLAY · SYNTHETIC · original time'), live: t('LIVE · agents réels · arrêt avant paiement', 'LIVE · real agents · stopping before payment')}[$('mode').value];
    $('agents').dataset.synthetic = String($('mode').value !== 'live');
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
    $('toast').querySelector('p').textContent = translate(errorCopy(err.status));
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
    const domains = new Set();
    for (const source of [...(race.source_urls || []), race.official_url]) {
      const href = safeURL(source); if (!href) continue;
      const domain = new URL(href).hostname.replace(/^www\./, '');
      if (domains.has(domain)) continue; domains.add(domain);
      row.append(link(href, `${new URL(href).hostname.replace(/^www\./, '')} ↗`, 'source-badge'));
    }
    if (race.retrieved_at && Number.isFinite(Date.parse(race.retrieved_at))) {
      const time = node('time', 'retrieved', `${t('Vérifié le', 'Checked on')} ${new Intl.DateTimeFormat(locale(), {day: 'numeric', month: 'short', timeZone: 'UTC'}).format(new Date(race.retrieved_at))}`);
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
        node('p', 'location', [flag(race), race.city, race.country].filter(Boolean).join(' · ')),
        node('p', 'countdown', countdown(race)),
        node('p', 'race-date', date(race.race_date)),
        node('span', 'date-status', race.date_status === 'official' ? 'Date officielle' : 'Date à confirmer'), sources(race));
      const warning = accessWarning(race); if (warning) card.append(warning); grid.append(card);
    }
    return grid;
  }
  function planCard(p, ready) {
    const card = node('section', 'plan-card'), head = node('div', 'plan-head');
    head.append(node('p', 'eyebrow', 'VOTRE LIGNE DE DÉPART'), node('h3', '', p.race.name),
      node('p', 'location', `${flag(p.race)} ${[p.race.city, p.race.country].filter(Boolean).join(' · ')} · ${distance(p.race)}`), node('p', 'countdown', countdown(p.race)), sources(p.race));
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
    if (['fr', 'en'].includes(turn.language)) language = turn.language;
    else detectLanguage(`${turn.assistant_message} ${turn.question}`);
    reply.inner.querySelectorAll('.pending').forEach(el => el.remove());
    reply.bubble.textContent = redact(clean(turn.assistant_message || t('Aucune proposition pour le moment. Essayons une autre envie de course.', 'No proposals yet. Let’s try another race idea.')));
    if (turn.plan) reply.inner.append(planCard(turn.plan, turn.ready_to_confirm));
    if (turn.candidates.length && (!turn.plan || !['official', 'unverified'].includes(turn.plan.race.date_status))) reply.inner.append(candidates(turn.candidates));
    if (turn.question) reply.inner.append(node('p', 'question', turn.question));
    const chips = node('div', 'chips'); chips.dataset.testid = 'chips';
    for (const suggestion of turn.suggestions) {
      if (!suggestion.id || !suggestion.label || suggestion.kind === 'confirm') continue;
      const race = suggestion.kind === 'choose_race' ? turn.candidates.find(r => r.id === suggestion.value || suggestion.id === `choose_race:${r.id}`) : null;
      const item = node('div', 'suggestion'), button = node('button', 'chip', `${race?.name || suggestion.label} ↗`);
      button.type = 'button'; button.onclick = () => send({suggestion_id: suggestion.id}, suggestion.label);
      const metadata = race ? `${distance(race)} · ${date(race.race_date)}` : {source: 'Course sourcée', synthetic: 'Exemple synthétique', suggested_default: 'Suggestion · modifiable'}[suggestion.provenance] || 'Choisir cette réponse';
      item.append(button, node('span', 'suggestion-meta', metadata)); chips.append(item);
    }
    if (chips.children.length) reply.inner.append(chips);
    const area = reply.inner.querySelector('.confirm-area'); if (area) reply.inner.append(area);
    localize(); badge(); scroll();
  }
  function loading(value) {
    busy = value; $('send').disabled = value; $('send').textContent = value ? '···' : '↑';
    document.querySelectorAll('.chip,.example-chips button,.confirm').forEach(b => { b.disabled = value || b.dataset.retired === 'true'; });
  }
  function pending(reply, started) {
    reply.bubble.textContent = translate('Je recherche les courses et leurs dates officielles. Vous n’avez pas besoin de connaître la date.');
    const box = node('div', 'pending'), progress = node('p', 'pending-copy', 'Recherche en cours · quelques instants…');
    const skeletons = node('div', 'skeletons'); skeletons.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 2; i++) { const card = node('div', 'skeleton'); card.append(node('span'), node('span'), node('span')); skeletons.append(card); }
    box.append(progress, skeletons); reply.inner.append(box); scroll();
    let clock;
    const tick = () => {
      const elapsed = Math.floor((Date.now() - started) / 1000);
      progress.textContent = t(`Recherche en cours · ${elapsed} s écoulées${elapsed >= 20 ? ' · les sources officielles peuvent prendre un peu de temps.' : ''}`, `Searching · ${elapsed} s elapsed${elapsed >= 20 ? ' · official sources can take a little time.' : ''}`);
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
      reply.bubble.textContent = translate('La recherche n’a pas abouti. Réessayez : votre demande est conservée.');
      error(err, () => send(body, label, attempt));
    } finally { stop(); if (token === generation) { loading(false); scroll(); } }
  }
  async function confirm(button) {
    if (busy || !mission?.ready_to_confirm) return;
    const token = generation; loading(true); button.textContent = translate('Lancement…');
    try {
      const result = await api(`/api/missions/${encodeURIComponent(mission.id)}/confirm`, {confirmed: true});
      if (token !== generation) return;
      mission.ready_to_confirm = false; document.querySelectorAll('.confirm-area,.chips').forEach(el => el.remove());
      $('agents').hidden = false; $('workspace').classList.add('executing');
      $('history-toggle').hidden = false; $('history-toggle').setAttribute('aria-expanded', 'false');
      consume(result); poll(token);
    } catch (err) { if (token === generation) { error(err); button.textContent = translate('Réessayer la confirmation'); } }
    finally { if (token === generation) loading(false); }
  }
  const cardFor = kind => document.querySelector(`[data-agent="${kind}"]`);
  function frameMeta(kind) {
    const state = agentState[kind], card = cardFor(kind); if (!state) return;
    const stale = state.stale || (state.received && Date.now() - state.received > 20000 && !terminal.has(state.status));
    const interrupted = state.pollFailed || ['blocked', 'failed', 'cancelled'].includes(state.status);
    const age = Math.max(0, Math.floor((Date.now() - (state.received || Date.now())) / 1000));
    const mode = $('mode').value;
    const status = state.image ? interrupted ? t('Image conservée · suivi interrompu', 'Image retained · tracking interrupted') : terminal.has(state.status) ? t('Dernière capture · agent arrêté', 'Last screenshot · agent stopped') : stale ? t(`L’agent travaille… dernière image il y a ${age}s`, `Agent working… last frame ${age}s ago`) : mode === 'live' ? t('Capture en direct', 'Live screenshot') : t('Capture SYNTHÉTIQUE', 'SYNTHETIC screenshot') : terminal.has(state.status) ? '' : t('En attente de la première capture', 'Waiting for the first screenshot');
    card.querySelector('.preview').dataset.state = state.image ? stale ? 'stale' : 'available' : 'unavailable';
    const time = state.image ? (mode === 'replay' ? state.recorded : state.observed) : null;
    const elapsed = state.started ? `${t('Durée', 'Elapsed')} ${Math.floor(((state.ended || Date.now()) - state.started) / 1000)}s` : '';
    card.querySelector('.frame-meta').textContent = `${status}${time && Number.isFinite(Date.parse(time)) ? ` · ${mode === 'replay' ? t('heure originale', 'original time') : t('observée', 'observed')} ${new Intl.DateTimeFormat(locale(), {hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC'}).format(new Date(time))} UTC` : ''}${elapsed ? `${status ? ' · ' : ''}${elapsed}` : ''}`;
    if (!state.image && terminal.has(state.status)) {
      const box = node('div', 'terminal-state');
      box.append(node('span', 'terminal-icon', state.status === 'ready_for_payment' ? '✓' : '↗'), node('strong', '', state.status === 'ready_for_payment' ? t('À vous de finaliser', 'Ready for you') : t('Reprenez la main', 'Over to you')));
      card.querySelector('.preview').replaceChildren(box);
    }
  }
  function loadFrame(kind, e) {
    if (typeof e.frame_id !== 'string' || !/^[a-zA-Z0-9_-]{1,160}$/.test(e.frame_id)) return;
    const state = agentState[kind], token = generation;
    if (state.requested === e.frame_id) return;
    state.requested = e.frame_id;
    const version = state.version = (state.version || 0) + 1;
    const img = new Image(); img.alt = `${$('mode').value === 'live' ? t('Navigateur de l’agent', 'Agent browser') : t('Illustration SYNTHÉTIQUE', 'SYNTHETIC illustration')} · ${kind}`; img.referrerPolicy = 'no-referrer';
    const current = () => token === generation && agentState[kind] === state && version === state.version;
    const fail = () => { if (current()) { state.stale = true; frameMeta(kind); } };
    img.onerror = fail;
    img.onload = async () => {
      try {
        if (img.decode) await img.decode(); if (!current()) return;
        state.image = img; state.stale = false; state.received = Date.now(); state.observed = e.observed_at; state.recorded = e.recorded_at;
        const preview = cardFor(kind).querySelector('.preview'), previous = preview.querySelector('img');
        preview.replaceChildren(img);
        if (previous && previous !== img) {
          previous.className = 'previous-frame'; preview.append(previous);
          setTimeout(() => previous.remove(), 450);
        }
        frameMeta(kind);
      } catch { fail(); }
    };
    img.src = `/api/frames/${encodeURIComponent(e.frame_id)}`;
  }
  function event(raw) {
    const e = {...raw, ...raw.data}; if (Number.isFinite(Number(e.sequence))) after = Math.max(after, Number(e.sequence));
    if (!kinds.includes(e.kind)) return;
    const state = agentState[e.kind] ||= {status: 'pending'}, card = cardFor(e.kind);
    state.started ||= Date.now();
    if (terminal.has(e.status)) state.status = e.status;
    else if (e.type === 'step_started' && !terminal.has(state.status)) state.status = 'running';
    if (terminal.has(state.status)) state.ended ||= Date.now();
    const pill = card.querySelector('.status'); pill.dataset.status = state.status;
    pill.textContent = state.status === 'running' ? t('EN DIRECT', 'LIVE') : translate(labels[state.status] || labels.pending);
    const heading = card.querySelector('h3'); if (heading) heading.textContent = {registration: t('Dossard', 'Bib'), hotel: t('Hôtel', 'Hotel'), transport: 'Transport'}[e.kind];
    const running = {registration: t('L’agent vérifie le parcours d’inscription.', 'Checking the registration journey.'), hotel: t('L’agent explore les hébergements pour votre séjour.', 'Exploring places to stay for your trip.'), transport: t('L’agent recherche votre trajet aller-retour.', 'Finding your outbound and return journey.')}[e.kind];
    state.reason = e.reason_code || state.reason;
    card.querySelector('.steps').textContent = state.status === 'ready_for_payment' ? t('✓ Prêt pour paiement — à finaliser par vous', '✓ Ready for payment — finish it yourself') : terminal.has(state.status) ? reason(state.reason, state.status) : state.status === 'running' ? running : t('L’agent se prépare.', 'The agent is getting ready.');
    if (e.type === 'live_frame' && e.frame_id) loadFrame(e.kind, e);
    const href = safeURL(e.handoff_url); if (href) state.handoff = href;
    const domain = state.handoff && new URL(state.handoff).hostname.replace(/^www\./, '');
    const handoff = link(state.handoff, t(`Continuer sur ${domain} ↗`, `Continue on ${domain} ↗`), 'handoff-link');
    if (handoff) card.querySelector('.handoff').replaceChildren(handoff);
    else if (terminal.has(state.status)) card.querySelector('.handoff').replaceChildren(node('p', 'no-site', t('Pas de site vérifié pour cette étape', 'No verified site for this step')));
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
    let eventsFailed = true;
    try {
      const events = await api(`/api/missions/${encodeURIComponent(mission.id)}/events?after=${after}`);
      eventsFailed = false;
      kinds.forEach(kind => { if (agentState[kind]) agentState[kind].pollFailed = false; });
      if (token !== generation) return; consume(events);
      const snapshot = await api(`/api/missions/${encodeURIComponent(mission.id)}`); if (token !== generation) return;
      const finished = consume(snapshot); kinds.forEach(frameMeta);
      if (!finished) timer = setTimeout(() => poll(token), 1000);
    } catch (err) {
      if (token !== generation) return;
      kinds.forEach(kind => { const state = agentState[kind]; if (state) { state.stale = true; state.pollFailed = eventsFailed; frameMeta(kind); } });
      error(err, () => poll(token));
    }
  }
  $('composer').onsubmit = e => { e.preventDefault(); const value = $('message').value.trim(); if (value) send({text: value}, value); };
  $('message').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('composer').requestSubmit(); } };
  $('message').oninput = () => { $('message').style.height = 'auto'; $('message').style.height = `${Math.min($('message').scrollHeight, 130)}px`; };
  document.querySelectorAll('[data-prompt]').forEach(button => { button.onclick = () => send({text: button.dataset.prompt}, button.dataset.prompt); });
  $('history-toggle').onclick = () => {
    const expanded = $('history-toggle').getAttribute('aria-expanded') !== 'true'; $('history-toggle').setAttribute('aria-expanded', String(expanded));
    $('workspace').classList[expanded ? 'add' : 'remove']('history-open'); $('history-toggle').textContent = translate(expanded ? 'Masquer la conversation ↑' : 'Voir le plan et la conversation ↓');
  };
  $('toast').querySelector('button').onclick = () => { $('toast').hidden = true; };
  $('mode').onchange = () => {
    generation++; clearTimeout(timer); mission = null; after = 0; language = globalThis.navigator?.language?.startsWith('en') ? 'en' : 'fr'; loading(false);
    for (const kind of kinds) delete agentState[kind];
    document.querySelectorAll('.message').forEach(el => el.remove());
    document.querySelectorAll('.agent').forEach(card => {
      card.querySelector('.preview').textContent = 'En attente de la première capture'; card.querySelector('.preview').dataset.state = 'unavailable';
      card.querySelector('.frame-meta').textContent = 'Aucune image reçue'; card.querySelector('.steps').textContent = 'L’agent se prépare.'; card.querySelector('.handoff').replaceChildren();
      const pill = card.querySelector('.status'); pill.dataset.status = 'pending'; pill.textContent = labels.pending;
    });
    $('welcome').hidden = false; $('agents').hidden = true; $('history-toggle').hidden = true;
    $('workspace').classList.remove('executing'); $('workspace').classList.remove('history-open'); $('message').value = ''; $('toast').hidden = true; localize(); badge();
  };
  globalThis.__runai = {event, consume, frameMeta, safeURL, reason, reasons, setLanguage: value => { language = value; localize(); badge(); }};
  localize(); badge(); const initialGeneration = generation;
  api('/api/health').then(health => {
    liveReady = health.live_ready || null;
    if (generation === initialGeneration && !mission && !busy && ['demo', 'replay', 'live'].includes(health.mode)) $('mode').value = health.mode;
    badge();
  }).catch(() => {});
})();
