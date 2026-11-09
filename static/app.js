(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const kinds = ['registration', 'hotel', 'transport'];
  const terminal = new Set(['ready_for_payment', 'blocked', 'failed', 'cancelled']);
  const labels = {pending: 'En attente', running: 'En action', ready_for_payment: 'Prêt', blocked: 'À reprendre', failed: 'Interrompu', cancelled: 'Arrêté'};
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
    'Inscription / dossard': 'Bib', 'Dossard': 'Bib', 'Hôtel': 'Hotel', 'En attente': 'Pending', 'En action': 'Working', 'À vous de jouer': 'Over to you', 'Prêt': 'Ready', 'À reprendre': 'Needs your help', 'Interrompu': 'Interrupted', 'Arrêté': 'Stopped',
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
    'Masquer la conversation ↑': 'Hide conversation ↑', 'Site choisi au lancement': 'Site picked at launch', 'Progression': 'Progress', 'Voir le plan et la conversation ↓': 'View plan and conversation ↓',
    'Ce service n’est pas disponible dans ce mode. Aucun résultat n’a été simulé.': 'This service is unavailable in this mode. No result was simulated.', 'Le plan a changé. Vérifiez la dernière proposition avant de continuer.': 'The plan changed. Check the latest proposal before continuing.',
    'Ce choix n’a pas pu être pris en compte. Essayez une autre réponse.': 'This choice could not be applied. Try another answer.', 'Cette session n’est plus disponible. Changez de mode pour recommencer.': 'This session is unavailable. Change mode to start again.', 'La connexion a été interrompue. Votre dernière étape est conservée.': 'Connection interrupted. Your last step is saved.'
  };
  const translate = value => {
    const raw = String(value ?? ''), key = raw.replace(/\s+/g, ' ').trim();
    if (language !== 'en' || !translations[key]) return raw;
    return `${/^\s/.test(raw) ? ' ' : ''}${translations[key]}${/\s$/.test(raw) ? ' ' : ''}`;
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
    no_site_coverage: ['Aucun site vérifié ne couvre encore cette étape.', 'Essayez une autre ville ou continuez sur le site officiel.', 'No reviewed site covers this step yet.', 'Try another city or continue on the official site.'],
    policy_denied: ['Ce site n’autorise pas les agents automatiques.', 'Continuez vous-même sur le site, en toute sécurité.', 'This site does not allow automated agents.', 'Continue on the site yourself, safely.'],
    date_mismatch: ['Les dates proposées ne correspondent pas à votre séjour.', 'Vérifiez les dates sur le site avant de réserver.', 'The dates offered do not match your trip.', 'Check the dates on the site before booking.'],
    no_inventory: ['Plus de disponibilité à ces dates.', 'Essayez d’autres dates ou une ville voisine.', 'No availability left for these dates.', 'Try other dates or a nearby city.'],
    sold_out: ['Course complète.', 'Choisissez une autre course ou suivez la liste d’attente officielle.', 'Race sold out.', 'Pick another race or follow the official waiting list.'],
    registration_closed: ['Les inscriptions sont fermées.', 'Choisissez une autre course ou la prochaine édition.', 'Registration is closed.', 'Pick another race or the next edition.'],
    login_required: ['Le site demande une connexion à votre compte.', 'Connectez-vous vous-même, puis reprenez sur le site.', 'The site asks you to sign in.', 'Sign in yourself, then continue on the site.'],
    captcha: ['Le site demande une vérification humaine.', 'Faites-la vous-même : l’agent ne la contourne jamais.', 'The site asks for a human check.', 'Complete it yourself: the agent never bypasses it.'],
    consent_required: ['Le site demande votre consentement.', 'Lisez et décidez vous-même : l’agent n’accepte jamais à votre place.', 'The site asks for your consent.', 'Read and decide yourself: the agent never accepts for you.'],
    unreviewed_redirect: ['Le site redirige vers un domaine non vérifié.', 'Par sécurité l’agent s’est arrêté : continuez depuis le site officiel.', 'The site redirects to an unreviewed domain.', 'The agent stopped for safety: continue from the official site.'],
    over_budget: ['Les offres trouvées dépassent votre budget.', 'Augmentez le budget ou réduisez le nombre de nuits.', 'The offers found exceed your budget.', 'Raise the budget or reduce the number of nights.'],
    step_limit: ['Le parcours était trop long pour être terminé à temps.', 'Reprenez directement sur le site.', 'The journey was too long to finish in time.', 'Continue directly on the site.'],
    session_failed: ['La session du navigateur s’est interrompue.', 'Relancez plus tard ou continuez sur le site.', 'The browser session was interrupted.', 'Try again later or continue on the site.'],
    timeout: ['Le site a mis trop de temps à répondre.', 'Réessayez plus tard ou continuez sur le site.', 'The site took too long to respond.', 'Try again later or continue on the site.'],
    unsafe_claim: ['Le résultat n’a pas pu être vérifié en sécurité.', 'Vérifiez vous-même sur le site avant tout paiement.', 'The result could not be safely verified.', 'Check it yourself on the site before paying.'],
    provider_error: ['Le service d’agents est momentanément indisponible.', 'Réessayez dans quelques minutes ou continuez sur le site.', 'The agent service is temporarily unavailable.', 'Try again in a few minutes or continue on the site.']
  };
  const kindReasons = {
    sold_out: {hotel: ['Hôtel complet à ces dates.', 'Hotel fully booked for these dates.'], transport: ['Trajets complets à ces dates.', 'Journeys sold out for these dates.']}
  };
  const reasonCopy = (code, status, kind) => {
    const entry = reasons[code], en = language === 'en';
    if (entry) return [kindReasons[code]?.[kind]?.[en ? 1 : 0] || entry[en ? 2 : 0], entry[en ? 3 : 1]];
    return [{
      blocked: t('Une étape nécessite votre intervention.', 'This step needs your help.'),
      failed: t('La préparation a été interrompue.', 'Preparation was interrupted.'),
      cancelled: t('L’agent est arrêté.', 'The agent was stopped.')
    }[status] || t('L’agent se prépare.', 'The agent is getting ready.'), terminal.has(status) ? t('Continuez sur le site officiel quand vous voulez.', 'Continue on the official site whenever you like.') : ''];
  };
  const reason = (code, status, kind) => reasonCopy(code, status, kind)[0];
  const countries = {italy: 'IT', italie: 'IT', italia: 'IT', france: 'FR', portugal: 'PT', spain: 'ES', espagne: 'ES', 'españa': 'ES', switzerland: 'CH', suisse: 'CH', schweiz: 'CH',
    germany: 'DE', allemagne: 'DE', deutschland: 'DE', belgium: 'BE', belgique: 'BE', netherlands: 'NL', 'pays-bas': 'NL', 'united kingdom': 'GB', 'royaume-uni': 'GB', uk: 'GB',
    austria: 'AT', autriche: 'AT', greece: 'GR', 'grèce': 'GR', ireland: 'IE', irlande: 'IE', denmark: 'DK', danemark: 'DK', sweden: 'SE', 'suède': 'SE', norway: 'NO', 'norvège': 'NO',
    'czech republic': 'CZ', czechia: 'CZ', 'république tchèque': 'CZ', poland: 'PL', pologne: 'PL', 'united states': 'US', usa: 'US', 'états-unis': 'US', japan: 'JP', japon: 'JP',
    morocco: 'MA', maroc: 'MA', luxembourg: 'LU', monaco: 'MC', hungary: 'HU', hongrie: 'HU', croatia: 'HR', croatie: 'HR', slovenia: 'SI', 'slovénie': 'SI'};
  const isoCountry = race => {
    const raw = String(race.country_code || race.country || '').trim();
    return /^[a-z]{2}$/i.test(raw) ? raw.toUpperCase() : countries[raw.toLowerCase()] || '';
  };
  const flag = race => { const code = isoCountry(race); return code ? [...code].map(c => String.fromCodePoint(127397 + c.charCodeAt())).join('') : ''; };
  const countdown = race => {
    const now = new Date(), days = Math.round((Date.parse(race.race_date) - Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000);
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
  const frenchWords = new Set('un une le la les des du de au aux en et ou pour avec sans je j tu il nous vous mon ma mes ton ta cet cette ce été printemps automne hiver semi course courses voudrais veux quel quelle laquelle combien depuis départ nuit nuits voilà ton séjour dans sur très ville prochain prochaine moi propose oui non merci'.split(' '));
  const englishWords = new Set('a an the in on of this that these i i\'d i\'m want would like race races half spring summer autumn fall winter from with which where how what your my next trip nights night city please yes no thanks let\'s here\'s some any near'.split(' '));
  function detectLanguage(value) {
    const words = String(value ?? '').toLowerCase().replace(/[’]/g, "'").split(/[^a-zà-ÿ']+/).filter(Boolean);
    let fr = (String(value ?? '').match(/[éèêàçùûôî]/gi) || []).length, en = 0;
    for (const word of words) { if (frenchWords.has(word)) fr++; if (englishWords.has(word)) en++; if (word.startsWith("j'") || word.startsWith("l'") || word.startsWith("d'")) fr++; }
    if (fr > en) language = 'fr'; else if (en > fr) language = 'en';
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
  const domainOf = value => { const href = safeURL(value); return href ? new URL(href).hostname.replace(/^www\./, '') : ''; };
  const agentNames = () => ({registration: t('Dossard', 'Bib'), hotel: t('Hôtel', 'Hotel'), transport: 'Transport'});
  const agentIcons = {registration: '↗', hotel: '⌂', transport: '→'};
  function prepState(value) {
    const raw = value && typeof value === 'object' ? value.status ?? value.state ?? (typeof value.covered === 'boolean' ? value.covered : null) : value;
    if (raw === true || ['covered', 'ready', 'ok', 'available', 'supported', 'open'].includes(raw)) return 'ok';
    if (['sold_out', 'full', 'complete'].includes(raw)) return 'sold_out';
    if (['closed', 'registration_closed'].includes(raw)) return 'closed';
    if (raw === false || ['uncovered', 'not_covered', 'none', 'unsupported', 'no_site_coverage', 'policy_denied'].includes(raw)) return 'none';
    return null;
  }
  const prepSite = value => value && typeof value === 'object' ? [value.site, value.host, value.domain].find(x => typeof x === 'string' && /^[a-z0-9.-]{3,120}$/i.test(x))?.replace(/^www\./, '') || '' : '';
  function prepBadges(race) {
    const prep = race?.preparation; if (!prep || typeof prep !== 'object') return null;
    const copy = {
      registration: {ok: t('Inscription ✓', 'Registration ✓'), sold_out: t('Complet', 'Sold out'), closed: t('Inscriptions fermées', 'Registration closed'), none: t('Inscription non couverte', 'Registration not covered')},
      hotel: {ok: t('Hôtel ✓', 'Hotel ✓'), sold_out: t('Hôtels complets', 'Hotels full'), closed: t('Hôtel non couvert', 'Hotel not covered'), none: t('Hôtel non couvert', 'Hotel not covered')},
      transport: {ok: t('Transport ✓', 'Transport ✓'), sold_out: t('Trajets complets', 'Journeys full'), closed: t('Transport non couvert', 'Transport not covered'), none: t('Transport non couvert', 'Transport not covered')}};
    const row = node('div', 'prep'); row.setAttribute('aria-label', t('Préparation possible', 'Preparation coverage'));
    for (const kind of kinds) {
      const state = prepState(prep[kind]); if (!state) continue;
      const badge = node('span', 'prep-badge', copy[kind][state]); badge.dataset.state = state; row.append(badge);
    }
    return row.children.length ? row : null;
  }
  function bigDistance(race) {
    const box = node('div', 'distance');
    if (Number.isFinite(race.distance_km)) box.append(node('span', 'num', new Intl.NumberFormat(locale(), {maximumFractionDigits: 1}).format(race.distance_km)), node('span', 'unit', ' km'));
    else box.append(node('span', 'num label', race.distance_label || 'Distance à confirmer'));
    return box;
  }
  function raceStats(race) {
    const stats = [[race.elevation_m ?? race.elevation_gain_m, v => `${new Intl.NumberFormat(locale()).format(v)} m D+`, t('Dénivelé', 'Elevation')],
      [race.field_size ?? race.participants, v => new Intl.NumberFormat(locale()).format(v), t('Coureurs', 'Runners')],
      [race.price_eur ?? race.entry_fee_eur, v => `${new Intl.NumberFormat(locale(), {maximumFractionDigits: 2}).format(v)} €`, t('Dossard', 'Entry')]]
      .filter(([value]) => Number.isFinite(value) && value > 0);
    if (!stats.length) return null;
    const row = node('dl', 'race-stats');
    for (const [value, format, label] of stats) { const item = node('div'); item.append(node('dt', '', label), node('dd', '', format(value))); row.append(item); }
    return row;
  }
  function raceWhen(race) {
    const when = node('div', 'race-when'), left = node('div');
    left.append(node('p', 'race-date', date(race.race_date)), node('span', 'date-status', race.date_status === 'official' ? 'Date officielle' : 'Date à confirmer'));
    when.append(left); const days = countdown(race); if (days) when.append(node('p', 'countdown', days));
    return when;
  }
  function candidates(items) {
    const grid = node('div', 'candidates');
    for (const race of items) {
      const card = node('article', 'candidate'), top = node('div', 'candidate-top');
      top.append(bigDistance(race), node('span', 'flag', flag(race)));
      card.append(top, node('h3', '', race.name || 'Course proposée'),
        node('p', 'location', [race.city, race.country].filter(Boolean).join(' · ')), raceWhen(race));
      for (const extra of [raceStats(race), prepBadges(race), sources(race), accessWarning(race)]) if (extra) card.append(extra);
      grid.append(card);
    }
    return grid;
  }
  function planCard(p, ready) {
    const card = node('section', 'plan-card'), head = node('div', 'plan-head');
    head.append(node('p', 'eyebrow', 'VOTRE LIGNE DE DÉPART'), node('h3', '', p.race.name),
      node('p', 'location', `${flag(p.race)} ${[p.race.city, p.race.country].filter(Boolean).join(' · ')} · ${distance(p.race)}`), raceWhen(p.race), sources(p.race));
    const prep = prepBadges(p.race); if (prep) head.append(prep);
    card.append(head);
    if (p.origin_city || p.race.city) {
      const route = node('div', 'route'), from = node('div', 'route-end'), to = node('div', 'route-end to');
      from.append(node('span', 'route-label', 'Départ'), node('strong', '', p.origin_city || '—'), node('span', 'route-date', p.arrival_date ? date(p.arrival_date) : ''));
      to.append(node('span', 'route-label', 'Course'), node('strong', '', p.race.city || p.race.name), node('span', 'route-date', p.departure_date ? `${t('Retour', 'Return')} ${date(p.departure_date)}` : ''));
      const line = node('div', 'route-line'); line.setAttribute('aria-hidden', 'true'); line.append(node('i'), node('b', '', '→'), node('i'));
      route.append(from, line, to); card.append(route);
    }
    const facts = node('dl', 'plan-facts');
    for (const [label, value] of [['Course', date(p.race.race_date)], ['Arrivée', p.arrival_date && date(p.arrival_date)],
      ['Retour', p.departure_date && date(p.departure_date)], ['Nuits', p.nights],
      [t('Voyageurs', 'Travellers'), Number.isInteger(p.travelers) ? p.travelers : null], ['Budget', p.budget_eur != null ? `${p.budget_eur} €` : null]]) {
      if (value == null) continue;
      const f = node('div', 'fact'); f.append(node('dt', '', label), node('dd', '', value)); facts.append(f);
    }
    card.append(facts);
    const crew = node('ul', 'plan-agents'); crew.setAttribute('aria-label', t('Les trois agents qui vont travailler', 'The three agents that will run'));
    const names = agentNames();
    for (const kind of kinds) {
      const site = prepSite(p.race.preparation?.[kind]) || (kind === 'registration' ? domainOf(p.race.registration_url || p.race.official_url) : '');
      const item = node('li'); item.append(node('span', 'agent-icon', agentIcons[kind]), node('strong', '', names[kind]), node('span', '', site || t('site choisi au lancement', 'site picked at launch')));
      crew.append(item);
    }
    card.append(crew, node('p', 'plan-note', 'Départ, nuits et budget : préférences modifiables, pas des disponibilités réservées.'));
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
    const typing = node('span', 'typing'); typing.setAttribute('aria-hidden', 'true'); typing.append(node('i'), node('i'), node('i'));
    box.append(typing, progress, skeletons); reply.inner.append(box); scroll();
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
    const token = generation; if (body.text) { detectLanguage(body.text); localize(); } loading(true); $('toast').hidden = true;
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
  const FRESH_MS = 15000;
  const duration = seconds => seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${String(seconds % 60).padStart(2, '0')}`;
  const stageLabels = () => [t('Démarrage', 'Starting'), t('Sur le site', 'On the site'), t('Sélection', 'Selecting')];
  function stepper(kind) {
    const state = agentState[kind], list = cardFor(kind).querySelector('.stepper'); if (!list || !state) return;
    const done = terminal.has(state.status), ready = state.status === 'ready_for_payment';
    const final = ready ? t('Prêt avant paiement', 'Ready before payment') : done ? t('Bloqué', 'Blocked') : t('Avant paiement', 'Before payment');
    const items = [...stageLabels(), final].map((label, index) => {
      const item = node('li', '', label);
      item.dataset.state = index === 3 ? (ready ? 'done' : done ? 'blocked' : 'todo')
        : ready || index < state.level ? 'done' : index === state.level ? (done ? 'done' : 'current') : 'todo';
      if (item.dataset.state === 'current') item.setAttribute('aria-current', 'step');
      return item;
    });
    if (state.level < 0 && done && !ready) items.slice(0, 3).forEach(item => { item.dataset.state = 'skipped'; });
    list.replaceChildren(...items);
  }
  function frameMeta(kind) {
    const state = agentState[kind], card = cardFor(kind); if (!state) return;
    const done = terminal.has(state.status), mode = $('mode').value;
    const age = state.received ? Math.max(0, Math.floor((Date.now() - state.received) / 1000)) : 0;
    const stale = state.image && !done && (state.stale || Date.now() - state.received >= FRESH_MS);
    const interrupted = state.pollFailed || ['blocked', 'failed', 'cancelled'].includes(state.status);
    const status = state.image ? interrupted ? t('Image conservée · suivi interrompu', 'Image retained · tracking interrupted')
      : done ? t('Dernière capture · agent arrêté', 'Last screenshot · agent stopped')
      : stale ? t(`L’agent travaille · image il y a ${age} s`, `Agent working · frame ${age} s ago`)
      : mode === 'live' ? t('EN DIRECT', 'LIVE') : t('SYNTHÉTIQUE · démo', 'SYNTHETIC · demo') : '';
    const badge = card.querySelector('.live-badge');
    if (badge) { badge.textContent = status; badge.hidden = !status; badge.dataset.tone = interrupted || done ? 'stopped' : stale ? 'stale' : mode === 'live' ? 'live' : 'synthetic'; }
    const preview = card.querySelector('.preview');
    preview.dataset.state = state.image ? stale ? 'stale' : 'available' : 'unavailable';
    const time = state.image ? (mode === 'replay' ? state.recorded : state.observed) : null;
    const clock = time && Number.isFinite(Date.parse(time)) ? `${mode === 'replay' ? t('heure originale', 'original time') : t('observée', 'observed')} ${new Intl.DateTimeFormat(locale(), {hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC'}).format(new Date(time))} UTC` : '';
    const seconds = state.started ? Math.floor(((state.ended || Date.now()) - state.started) / 1000) : 0;
    const elapsed = done && !state.active ? t('Non démarré', 'Not started') : !state.started ? '' : done ? seconds < 1 ? t('Terminé', 'Finished') : t(`Terminé en ${duration(seconds)}`, `Finished in ${duration(seconds)}`) : t(`Durée ${duration(seconds)}`, `Elapsed ${duration(seconds)}`);
    const meta = [!state.image && !done ? t('En attente de la première capture', 'Waiting for the first screenshot') : '', clock, elapsed].filter(Boolean).join(' · ');
    card.querySelector('.frame-meta').textContent = meta;
    if (!state.image && done) {
      const box = node('div', 'terminal-state'), ready = state.status === 'ready_for_payment';
      box.append(node('span', 'terminal-icon', ready ? '✓' : state.active ? '!' : '–'),
        node('strong', '', ready ? t('Prêt avant paiement', 'Ready before payment') : state.active ? t('Reprenez la main', 'Over to you') : t('Non démarré', 'Not started')));
      preview.replaceChildren(box);
    } else if (!state.image && !preview.querySelector('.waiting')) {
      const box = node('div', 'waiting'); box.append(node('span', 'pulse-dot'), node('span', '', t('Ouverture du navigateur de l’agent…', 'Opening the agent’s browser…')));
      preview.replaceChildren(box);
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
  const tripFacts = () => mission?.trip || mission?.plan || {};
  const shownTotal = summary => {
    const match = /(?:€\s?(\d{1,5}(?:[.,]\d{1,2})?)|(\d{1,5}(?:[.,]\d{1,2})?)\s?(?:€|EUR\b))/i.exec(String(summary ?? ''));
    return match ? `${match[1] || match[2]} €` : '';
  };
  function successBox(kind, state) {
    const box = node('div', 'success'), domain = domainOf(state.handoff), trip = tripFacts();
    const check = node('span', 'success-check', '✓'); check.setAttribute('aria-hidden', 'true');
    const facts = [];
    if (kind === 'registration' && trip.race?.race_date) facts.push(date(trip.race.race_date));
    if (kind !== 'registration' && trip.arrival_date && trip.departure_date) facts.push(`${date(trip.arrival_date)} → ${date(trip.departure_date)}`);
    if (Number.isInteger(trip.travelers)) facts.push(t(`${trip.travelers} voyageur${trip.travelers > 1 ? 's' : ''}`, `${trip.travelers} traveller${trip.travelers > 1 ? 's' : ''}`));
    if (state.total) facts.push(t(`total affiché ${state.total}`, `total shown ${state.total}`));
    const head = node('div', 'success-head'); head.append(check, node('strong', '', t('Prêt avant paiement', 'Ready before payment')));
    box.append(head);
    if (facts.length) box.append(node('p', 'success-facts', facts.join(' · ')));
    const cta = link(state.handoff, t(`Prêt — à vous de payer sur ${domain} ↗`, `Ready — pay yourself on ${domain} ↗`), 'handoff-link cta');
    if (cta) box.append(cta);
    if ($('mode').value !== 'live') box.append(node('p', 'success-note', t('Démo synthétique : page d’accueil publique, aucun panier réel.', 'Synthetic demo: public homepage, no real checkout.')));
    return box;
  }
  function render(kind) {
    const state = agentState[kind], card = cardFor(kind); if (!state || !card) return;
    card.dataset.status = state.status;
    const pill = card.querySelector('.status'); pill.dataset.status = state.status; pill.textContent = translate(labels[state.status] || labels.pending);
    const heading = card.querySelector('h3'); if (heading) heading.textContent = agentNames()[kind];
    const site = card.querySelector('.site');
    if (site) site.textContent = state.site ? `${state.alternative ? t('Autre site · ', 'Alternative · ') : ''}${state.site}` : terminal.has(state.status) && !state.active ? t('Aucun site ouvert', 'No site opened') : t('Site choisi au lancement', 'Site picked at launch');
    stepper(kind);
    const steps = card.querySelector('.steps'), handoff = card.querySelector('.handoff');
    const running = {registration: t('Vérifie le parcours d’inscription officiel.', 'Checking the official registration journey.'), hotel: t('Compare les chambres pour vos dates.', 'Comparing rooms for your dates.'), transport: t('Cherche votre aller-retour.', 'Finding your outbound and return journey.')}[kind];
    if (state.status === 'ready_for_payment') steps.textContent = kind === 'registration' ? t('Prêt : vous complétez vous-même l’inscription, puis payez.', 'Ready: you complete the registration details yourself, then pay.') : t('Tout est prêt : il ne reste que le paiement, par vous.', 'All set: only the payment is left, for you.');
    else if (terminal.has(state.status)) {
      const [title, next] = reasonCopy(state.reason, state.status, kind);
      steps.replaceChildren(node('strong', 'reason-title', title), ...(next ? [node('span', 'reason-next', next)] : []));
    } else steps.textContent = state.status === 'running' ? state.alternative ? t('Essai d’un autre site…', 'Trying another site…') : running : t('L’agent se prépare.', 'The agent is getting ready.');
    if (state.status === 'ready_for_payment') handoff.replaceChildren(successBox(kind, state));
    else {
      const domain = domainOf(state.handoff), next = link(state.handoff, t(`Continuer sur ${domain} ↗`, `Continue on ${domain} ↗`), 'handoff-link');
      if (next) handoff.replaceChildren(next);
      else if (terminal.has(state.status)) handoff.replaceChildren(node('p', 'no-site', t('Pas de site vérifié pour cette étape', 'No verified site for this step')));
    }
    frameMeta(kind);
  }
  function changeChips() {
    const trip = tripFacts(), race = trip.race || {}, km = Number.isFinite(race.distance_km) ? distance(race) : race.distance_label || '';
    return [
      [t('Une autre course', 'Another race'), km && race.country ? t(`Propose-moi une autre course de ${km} en ${race.country}`, `Suggest another ${km} race in ${race.country}`) : t('Propose-moi une autre course', 'Suggest another race')],
      [t('Une autre ville', 'Another city'), km ? t(`Propose-moi un ${km} dans une autre ville${race.country ? ` en ${race.country}` : ''}`, `Suggest a ${km} race in a different city${race.country ? ` in ${race.country}` : ''}`) : t('Une course dans une autre ville', 'A race in another city')],
      [t('Un autre départ', 'Another origin'), race.name && trip.origin_city ? t(`${race.name}, en partant d’une autre ville que ${trip.origin_city}`, `${race.name}, leaving from another city than ${trip.origin_city}`) : t('Je pars d’une autre ville', 'I am leaving from another city')]
    ];
  }
  const coverageReasons = new Set(['no_site_coverage', 'policy_denied']);
  function overview() {
    const states = kinds.map(kind => agentState[kind]), finished = states.every(state => state && terminal.has(state.status));
    const ready = states.filter(state => state?.status === 'ready_for_payment').length, banner = $('mission-banner'), coverage = $('coverage');
    const dead = finished && !ready && states.every(state => !state.active && coverageReasons.has(state.reason));
    $('agents').dataset.view = dead ? 'coverage' : 'agents';
    banner.hidden = !finished || dead;
    if (finished && !dead) {
      banner.dataset.tone = ready === 3 ? 'success' : 'partial';
      banner.replaceChildren(node('strong', '', ready === 3 ? t('Tout est prêt avant paiement', 'Everything is ready before payment') : t(`${ready}/3 prêt${ready > 1 ? 's' : ''} avant paiement`, `${ready}/3 ready before payment`)),
        node('span', '', ready === 3 ? t('Les trois étapes vous attendent : vous complétez vos informations et payez vous-même, sur chaque site.', 'All three steps are waiting: you enter your details and pay yourself, on each site.') : t('Reprenez les autres étapes sur les sites proposés.', 'Continue the other steps on the suggested sites.')));
    }
    coverage.hidden = !dead;
    if (!dead || coverage.dataset.rendered === 'true') return;
    coverage.dataset.rendered = 'true';
    const list = node('ul', 'coverage-reasons'), names = agentNames(), links = node('div', 'coverage-links'), seen = new Set();
    for (const kind of kinds) {
      const item = node('li'); item.append(node('span', 'agent-icon', agentIcons[kind]), node('strong', '', names[kind]), node('span', '', reason(agentState[kind].reason, agentState[kind].status, kind)));
      list.append(item);
      const domain = domainOf(agentState[kind].handoff);
      if (domain && !seen.has(domain)) { seen.add(domain); const a = link(agentState[kind].handoff, t(`${names[kind]} · ${domain} ↗`, `${names[kind]} · ${domain} ↗`), 'source-badge'); if (a) links.append(a); }
    }
    const chips = node('div', 'chips coverage-chips');
    for (const [label, text] of changeChips()) {
      const item = node('div', 'suggestion'), button = node('button', 'chip', `${label} ↗`);
      button.type = 'button'; button.onclick = () => restart(text);
      item.append(button, node('span', 'suggestion-meta', text)); chips.append(item);
    }
    coverage.replaceChildren(node('span', 'coverage-icon', '↺'), node('p', 'eyebrow', t('COUVERTURE', 'COVERAGE')),
      node('h3', '', t('Ce voyage n’est pas encore couvert par nos agents', 'Our agents do not cover this trip yet')),
      node('p', 'coverage-copy', t('Aucun agent n’a pu démarrer : nos sites vérifiés ne couvrent pas encore cette course, cette ville ou ce départ. Rien n’a été réservé ni envoyé.', 'No agent could start: our reviewed sites do not cover this race, city or origin yet. Nothing was booked or sent.')),
      list, ...(links.children.length ? [links] : []), node('p', 'question', t('On essaie autre chose ?', 'Shall we try something else?')), chips);
  }
  function event(raw) {
    const e = {...raw, ...raw.data}; if (Number.isFinite(Number(e.sequence))) after = Math.max(after, Number(e.sequence));
    if (!kinds.includes(e.kind)) return;
    const state = agentState[e.kind] ||= {status: 'pending', level: -1, frames: 0, progress: 0};
    const message = String(e.message ?? '');
    if (e.type === 'step_started') { state.started ||= Date.now(); state.level = Math.max(state.level, 0); }
    if (e.type === 'live_frame' || (e.type === 'step_progress' && !/unavailable|size limit/i.test(message))) {
      state.active = true; state.started ||= Date.now();
      if (e.type === 'live_frame') state.frames++; else state.progress++;
      state.level = Math.max(state.level, state.frames >= 3 || state.progress >= 3 ? 2 : 1);
    }
    if (e.type === 'step_progress' && (e.alternative === true || /alternativ|another site|autre site|fallback/i.test(message))) state.alternative = true;
    if (terminal.has(e.status)) state.status = e.status;
    else if (e.type === 'step_started' && !terminal.has(state.status)) state.status = 'running';
    if (terminal.has(state.status)) state.ended ||= Date.now();
    if (terminal.has(e.status)) { state.reason = e.reason_code || state.reason; state.total = shownTotal(e.summary) || state.total; }
    const visited = domainOf(e.final_url) || domainOf(e.site_url) || domainOf(e.start_url);
    if (visited) state.site = visited;
    const href = safeURL(e.handoff_url); if (href) state.handoff = href;
    if (!state.site && state.active && state.handoff) state.site = domainOf(state.handoff);
    render(e.kind);
    if (e.type === 'live_frame' && e.frame_id) loadFrame(e.kind, e);
    overview();
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
  function resetStage() {
    for (const kind of kinds) delete agentState[kind];
    document.querySelectorAll('.agent').forEach(card => {
      card.dataset.status = 'pending';
      card.querySelector('.preview').textContent = translate('En attente de la première capture'); card.querySelector('.preview').dataset.state = 'unavailable';
      card.querySelector('.frame-meta').textContent = translate('Aucune image reçue'); card.querySelector('.steps').textContent = translate('L’agent se prépare.'); card.querySelector('.handoff').replaceChildren();
      const pill = card.querySelector('.status'); pill.dataset.status = 'pending'; pill.textContent = translate(labels.pending);
      for (const [cls, value] of [['.site', 'Site choisi au lancement'], ['.live-badge', '']]) { const el = card.querySelector(cls); if (el) { el.textContent = translate(value); if (cls === '.live-badge') el.hidden = true; } }
      card.querySelector('.stepper')?.replaceChildren();
    });
    $('mission-banner').hidden = true; $('coverage').hidden = true; $('coverage').replaceChildren(); $('coverage').dataset.rendered = 'false'; $('agents').dataset.view = 'agents';
    $('agents').hidden = true; $('history-toggle').hidden = true; $('history-toggle').setAttribute('aria-expanded', 'false');
    $('workspace').classList.remove('executing'); $('workspace').classList.remove('history-open');
  }
  function restart(text) {
    generation++; clearTimeout(timer); mission = null; after = 0; loading(false); resetStage(); send({text}, text);
  }
  $('mode').onchange = () => {
    generation++; clearTimeout(timer); mission = null; after = 0; language = globalThis.navigator?.language?.startsWith('en') ? 'en' : 'fr'; loading(false);
    resetStage(); document.querySelectorAll('.message').forEach(el => el.remove());
    $('welcome').hidden = false; $('message').value = ''; $('toast').hidden = true; localize(); badge();
  };
  function demoFrame(kind) {
    const state = agentState[kind], label = {registration: 'REGISTRATION', hotel: 'HOTEL', transport: 'TRANSPORT'}[kind];
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><rect width="800" height="500" fill="#1d1d22"/><rect x="40" y="40" width="720" height="10" rx="5" fill="#fc4c02"/><text x="40" y="120" fill="#fff" font-family="Arial" font-size="40" font-weight="700">${label}</text><text x="40" y="180" fill="#c9c9d2" font-family="Arial" font-size="24">SYNTHETIC demo screen · not a real site</text><rect x="40" y="230" width="460" height="24" rx="12" fill="#33333b"/><rect x="40" y="280" width="340" height="24" rx="12" fill="#33333b"/></svg>`;
    const img = new Image(); img.alt = `${t('Illustration SYNTHÉTIQUE', 'SYNTHETIC illustration')} · ${kind}`;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    state.image = img; state.received = Date.now(); state.stale = false;
    cardFor(kind).querySelector('.preview').replaceChildren(img); frameMeta(kind);
  }
  function demoStage(name) {
    if ($('mode').value === 'live') return false;
    $('agents').hidden = false; $('workspace').classList.add('executing'); $('history-toggle').hidden = false;
    const fake = (kind, data) => event({kind, synthetic: true, ...data});
    if (name === 'stale') kinds.forEach(kind => { const state = agentState[kind]; if (state?.received) { state.received -= FRESH_MS + 7000; frameMeta(kind); } });
    else if (name === 'alternative') fake('hotel', {type: 'step_progress', message: 'SYNTHETIC: trying alternative site'});
    else {
      resetStage(); $('agents').hidden = false; $('workspace').classList.add('executing'); $('history-toggle').hidden = false;
      const codes = name === 'coverage' ? ['no_site_coverage', 'no_site_coverage', 'policy_denied'] : ['sold_out', 'no_inventory', 'captcha'];
      kinds.forEach((kind, index) => {
        fake(kind, {type: 'step_started'});
        if (name === 'coverage') { fake(kind, {status: 'blocked', reason_code: codes[index], handoff_url: index ? null : 'https://example.com/runai-synthetic/registration'}); return; }
        fake(kind, {type: 'step_progress', message: 'SYNTHETIC: opening site', start_url: `https://example.com/runai-synthetic/${kind}`});
        if (name === 'running') { demoFrame(kind); return; }
        fake(kind, {type: 'step_progress', message: 'SYNTHETIC: reviewing'}); fake(kind, {type: 'step_progress', message: 'SYNTHETIC: selecting'});
        fake(kind, name === 'success' ? {status: 'ready_for_payment', summary: kind === 'registration' ? '' : 'SYNTHETIC total 312 €', handoff_url: `https://example.com/runai-synthetic/${kind}`}
          : {status: 'blocked', reason_code: codes[index], handoff_url: `https://example.com/runai-synthetic/${kind}`});
      });
    }
    return true;
  }
  globalThis.__runai = {event, consume, frameMeta, safeURL, reason, reasonCopy, reasons, detectLanguage: value => { detectLanguage(value); return language; }, demo: demoStage, translate, setLanguage: value => { language = value; localize(); badge(); }};
  localize(); badge(); const initialGeneration = generation;
  api('/api/health').then(health => {
    liveReady = health.live_ready || null;
    if (generation === initialGeneration && !mission && !busy && ['demo', 'replay', 'live'].includes(health.mode)) $('mode').value = health.mode;
    badge();
  }).catch(() => {});
})();
