(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const kinds = ['registration', 'hotel', 'transport'];
  const terminal = new Set(['ready_for_payment', 'blocked', 'failed', 'cancelled']);
  const labels = {pending: 'En attente', queued: 'En file', running: 'En action', ready_for_payment: 'Prêt', blocked: 'À reprendre', failed: 'Interrompu', cancelled: 'Arrêté'};
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
    'Inscription / dossard': 'Bib', 'Dossard': 'Bib', 'Hôtel': 'Hotel', 'En attente': 'Pending', 'En action': 'Working', 'À vous de jouer': 'Over to you', 'Prêt': 'Ready', 'À reprendre': 'Needs your help', 'Interrompu': 'Interrupted', 'Arrêté': 'Stopped', 'En file': 'Queued', 'Agrandir l’agent Dossard': 'Enlarge Bib agent', 'Agrandir l’agent Hôtel': 'Enlarge Hotel agent', 'Agrandir l’agent Transport': 'Enlarge Transport agent', 'Progression des agents': 'Agent progress',
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
    'Ce choix n’a pas pu être pris en compte. Essayez une autre réponse.': 'This choice could not be applied. Try another answer.', 'Cette session n’est plus disponible. Changez de mode pour recommencer.': 'This session is unavailable. Change mode to start again.', 'La connexion a été interrompue. Votre dernière étape est conservée.': 'Connection interrupted. Your last step is saved.',
    'Modifier le plan… (ex. départ de Lyon, 3 nuits)': 'Edit the plan… (e.g. leaving from Lyon, 3 nights)', 'Choisissez une course ou précisez votre envie…': 'Pick a race or refine your wish…',
    'PROFIL COUREUR · UNE SEULE FOIS': 'RUNNER PROFILE · ONCE', 'Vos infos, saisies pour vous': 'Your details, typed for you', 'Remplir avec un profil de test': 'Fill with a test profile', 'Continuer sans profil': 'Continue without profile',
    'Les agents tapent ces informations dans les formulaires participant, voyageur et client pour aller le plus loin possible.': 'Agents type these details into participant, traveller and guest forms to get as far as possible.',
    'Gardé en mémoire pour cette mission uniquement, saisi par les agents dans les formulaires, jamais enregistré. Aucun paiement, compte ni consentement.': 'Kept in memory for this mission only, typed by the agents into forms, never stored. No payment, account or consent.',
    'Enregistrer pour cette mission ↗': 'Use for this mission ↗', 'Nom complet': 'Full name', 'E-mail': 'Email', 'Téléphone': 'Phone', 'Date de naissance': 'Birth date', 'Genre': 'Gender', 'Nationalité': 'Nationality', 'Adresse (optionnelle)': 'Address (optional)',
    'Choisir': 'Choose', 'Femme': 'Female', 'Homme': 'Male', 'Non précisé': 'Not specified'
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
  const clean = value => String(value ?? '').replace(/\s*[—–-]?\s*(?:accès inconnu|access unknown)/gi, '').replace(/\[\s*synth[ée]tique\s*\/\s*synthetic\s*\]\s*/gi, '');
  const reasons = {
    not_yet_bookable: ['Billets pas encore en vente · réessaie plus près de la date', 'Consultez les horaires en attendant.', 'Tickets not on sale yet · try again closer to the date', 'Check the timetable in the meantime.'],
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
    provider_error: ['Le service d’agents est momentanément indisponible.', 'Réessayez dans quelques minutes ou continuez sur le site.', 'The agent service is temporarily unavailable.', 'Try again in a few minutes or continue on the site.'],
    checkpoint_unverified: ['Étape de réservation atteinte — à vérifier', 'Vérifiez les dates et votre sélection sur le site avant de continuer.', 'Booking step reached — please verify', 'Check your dates and selection on the site before continuing.'],
    checkpoint_reached: ['Étape de réservation atteinte — à vérifier', 'La page est ouverte : vérifiez les détails avant tout engagement.', 'Booking step reached — please verify', 'The page is open: check the details before any commitment.']
  };
  const boundaryReason = ['L’agent s’est arrêté à la limite de ce qu’il a le droit de faire sur ce site.', 'Il ne va jamais plus loin sans vous : reprenez à cette étape sur le site.', 'The agent stopped at the edge of what it may do on this site.', 'It never goes further without you: continue from this step on the site.'];
  const kindReasons = {
    sold_out: {hotel: ['Hôtel complet à ces dates.', 'Hotel fully booked for these dates.'], transport: ['Trajets complets à ces dates.', 'Journeys sold out for these dates.']}
  };
  const reasonCopy = (code, status, kind, active = false) => {
    const entry = code === 'policy_denied' && active ? boundaryReason : reasons[code], en = language === 'en';
    if (entry) return [kindReasons[code]?.[kind]?.[en ? 1 : 0] || entry[en ? 2 : 0], entry[en ? 3 : 1]];
    return [{
      blocked: t('Une étape nécessite votre intervention.', 'This step needs your help.'),
      failed: t('La préparation a été interrompue.', 'Preparation was interrupted.'),
      cancelled: t('L’agent est arrêté.', 'The agent was stopped.')
    }[status] || t('L’agent se prépare.', 'The agent is getting ready.'), terminal.has(status) ? t('Continuez sur le site officiel quand vous voulez.', 'Continue on the official site whenever you like.') : ''];
  };
  const reason = (code, status, kind, active) => reasonCopy(code, status, kind, active)[0];
  const countries = {italy: 'IT', italie: 'IT', italia: 'IT', france: 'FR', portugal: 'PT', spain: 'ES', espagne: 'ES', 'españa': 'ES', switzerland: 'CH', suisse: 'CH', schweiz: 'CH',
    germany: 'DE', allemagne: 'DE', deutschland: 'DE', belgium: 'BE', belgique: 'BE', netherlands: 'NL', 'pays-bas': 'NL', 'united kingdom': 'GB', 'royaume-uni': 'GB', uk: 'GB',
    austria: 'AT', autriche: 'AT', greece: 'GR', 'grèce': 'GR', ireland: 'IE', irlande: 'IE', denmark: 'DK', danemark: 'DK', sweden: 'SE', 'suède': 'SE', norway: 'NO', 'norvège': 'NO',
    'czech republic': 'CZ', czechia: 'CZ', 'république tchèque': 'CZ', poland: 'PL', pologne: 'PL', 'united states': 'US', usa: 'US', 'états-unis': 'US', japan: 'JP', japon: 'JP',
    morocco: 'MA', maroc: 'MA', luxembourg: 'LU', monaco: 'MC', hungary: 'HU', hongrie: 'HU', croatia: 'HR', croatie: 'HR', slovenia: 'SI', 'slovénie': 'SI'};
  const isoCountry = race => {
    const raw = String(race.country_code || race.country || '').trim();
    return /^[a-z]{2}$/i.test(raw) ? raw.toUpperCase() : countries[raw.toLowerCase()] || '';
  };
  const flagShapes = {
    IT: [['rect', {width: 24, height: 16, fill: '#fff'}], ['rect', {width: 8, height: 16, fill: '#009246'}], ['rect', {x: 16, width: 8, height: 16, fill: '#ce2b37'}]],
    FR: [['rect', {width: 24, height: 16, fill: '#fff'}], ['rect', {width: 8, height: 16, fill: '#002395'}], ['rect', {x: 16, width: 8, height: 16, fill: '#ed2939'}]],
    BE: [['rect', {width: 24, height: 16, fill: '#fdda24'}], ['rect', {width: 8, height: 16, fill: '#161616'}], ['rect', {x: 16, width: 8, height: 16, fill: '#ef3340'}]],
    DE: [['rect', {width: 24, height: 16, fill: '#ffce00'}], ['rect', {width: 24, height: 10.67, fill: '#d00'}], ['rect', {width: 24, height: 5.33, fill: '#161616'}]],
    NL: [['rect', {width: 24, height: 16, fill: '#21468b'}], ['rect', {width: 24, height: 10.67, fill: '#fff'}], ['rect', {width: 24, height: 5.33, fill: '#ae1c28'}]],
    CH: [['rect', {width: 24, height: 16, fill: '#da291c'}], ['path', {d: 'M10 3h4v3h3v4h-3v3h-4v-3H7V6h3z', fill: '#fff'}]],
    ES: [['rect', {width: 24, height: 16, fill: '#aa151b'}], ['rect', {y: 4, width: 24, height: 8, fill: '#f1bf00'}], ['path', {d: 'M6 6h3v4L7.5 11 6 10z', fill: '#aa151b'}]],
    PT: [['rect', {width: 24, height: 16, fill: '#f00'}], ['rect', {width: 9.6, height: 16, fill: '#006600'}], ['circle', {cx: 9.6, cy: 8, r: 3.5, fill: '#ffdf00'}], ['path', {d: 'M8 5.5h3.2v4L9.6 11 8 9.5z', fill: '#fff', stroke: '#c00', 'stroke-width': .8}]]
  };
  function flag(race) {
    const code = isoCountry(race); if (!code) return null;
    const shapes = flagShapes[code], el = shapes ? document.createElementNS('http://www.w3.org/2000/svg', 'svg') : node('span', 'flag flag-fallback', code);
    el.setAttribute('class', shapes ? 'flag' : 'flag flag-fallback');
    el.setAttribute('role', 'img'); el.setAttribute('aria-label', code); el.dataset.country = code;
    if (shapes) {
      el.setAttribute('viewBox', '0 0 24 16'); el.setAttribute('width', '24'); el.setAttribute('height', '16'); el.setAttribute('focusable', 'false');
      for (const [tag, attributes] of shapes) {
        const shape = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [key, value] of Object.entries(attributes)) shape.setAttribute(key, String(value));
        el.append(shape);
      }
    }
    return el;
  }
  const countdown = race => {
    const now = new Date(), days = Math.round((Date.parse(race.race_date) - Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000);
    return !Number.isFinite(days) || days < 0 ? '' : days === 0 ? t('aujourd’hui', 'today') : t(`dans ${days} j`, `in ${days} day${days > 1 ? 's' : ''}`);
  };
  const cityNames = [['Genève', 'Geneva', 'geneve', 'genf', 'ginevra'], ['Milan', 'Milan', 'milano'], ['Lisbonne', 'Lisbon', 'lisboa'], ['Barcelone', 'Barcelona'],
    ['La Haye', 'The Hague', 'den haag', "'s-gravenhage", 'hague'], ['Rome', 'Rome', 'roma'], ['Florence', 'Florence', 'firenze'], ['Venise', 'Venice', 'venezia'],
    ['Turin', 'Turin', 'torino'], ['Naples', 'Naples', 'napoli'], ['Séville', 'Seville', 'sevilla'], ['Valence', 'Valencia'], ['Munich', 'Munich', 'münchen', 'muenchen'],
    ['Vienne', 'Vienna', 'wien'], ['Bruxelles', 'Brussels', 'brussel'], ['Anvers', 'Antwerp', 'antwerpen'], ['Copenhague', 'Copenhagen', 'københavn'], ['Prague', 'Prague', 'praha'],
    ['Londres', 'London'], ['Zurich', 'Zurich', 'zürich'], ['Berne', 'Bern'], ['Lucerne', 'Lucerne', 'luzern'], ['Bâle', 'Basel', 'basle'], ['Athènes', 'Athens', 'athina'],
    ['Varsovie', 'Warsaw', 'warszawa'], ['Cologne', 'Cologne', 'köln', 'koeln'], ['Francfort', 'Frankfurt', 'frankfurt am main'], ['Édimbourg', 'Edinburgh'], ['Dublin', 'Dublin'],
    ['Amsterdam', 'Amsterdam'], ['Berlin', 'Berlin'], ['Paris', 'Paris'], ['Lyon', 'Lyon'], ['Marseille', 'Marseille'], ['Nice', 'Nice'], ['Bordeaux', 'Bordeaux'], ['Porto', 'Porto'], ['Madrid', 'Madrid']]
    .reduce((map, entry) => { for (const alias of entry) map[alias.toLowerCase()] = entry; return map; }, {});
  const cityName = value => { const raw = String(value ?? '').trim(), entry = cityNames[raw.toLowerCase()]; return entry ? entry[language === 'en' ? 1 : 0] : raw; };
  const countryName = race => {
    const code = isoCountry(race);
    try { if (code && Intl.DisplayNames) return new Intl.DisplayNames([locale()], {type: 'region'}).of(code) || race.country || ''; } catch { /* fall back */ }
    return race.country || '';
  };
  const place = race => [cityName(race.city), countryName(race)].filter(Boolean).join(' · ');
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
      language: envelope.language, mode: ['demo', 'replay', 'live'].includes(envelope.mode) ? envelope.mode : undefined,
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
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw Object.assign(new Error('Request failed'), {status: response.status, detail: data.detail});
      }
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
  function accessWarning(race, plan = false) {
    if (plan && (race.date_status !== 'official' || !race.race_date))
      return node('p', 'access-warning', t('Date pas encore confirmée par une source officielle : les agents attendent une date officielle avant de préparer quoi que ce soit.', 'Date not yet confirmed by an official source: the agents wait for an official date before preparing anything.'));
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
    if (raw === 'not_open') return 'not_open';
    if (raw === false || ['uncovered', 'not_covered', 'none', 'unsupported', 'no_site_coverage', 'policy_denied', 'prohibited'].includes(raw)) return 'none';
    return null;
  }
  const prepSite = value => value && typeof value === 'object' ? [value.site, value.host, value.domain].find(x => typeof x === 'string' && /^[a-z0-9.-]{3,120}$/i.test(x))?.replace(/^www\./, '') || '' : '';
  function prepBadges(race) {
    const prep = race?.preparation; if (!prep || typeof prep !== 'object') return null;
    const copy = {
      registration: {ok: t('Inscription ✓', 'Registration ✓'), sold_out: t('Complet', 'Sold out'), closed: t('Inscriptions fermées', 'Registration closed'), not_open: t('Inscriptions bientôt ouvertes', 'Registration opens soon'), none: t('Inscription non couverte', 'Registration not covered')},
      hotel: {ok: t('Hôtel ✓', 'Hotel ✓'), sold_out: t('Hôtels complets', 'Hotels full'), closed: t('Hôtel non couvert', 'Hotel not covered'), none: t('Hôtel non couvert', 'Hotel not covered')},
      transport: {ok: t('Transport ✓', 'Transport ✓'), sold_out: t('Trajets complets', 'Journeys full'), closed: t('Transport non couvert', 'Transport not covered'), none: t('Transport non couvert', 'Transport not covered')}};
    const row = node('div', 'prep'); row.setAttribute('aria-label', t('Préparation possible', 'Preparation coverage'));
    const trusted = race.date_status === 'official' && prepState(prep.registration) === 'ok';
    for (const kind of kinds) {
      const state = prepState(prep[kind]); if (!state || (state === 'ok' && !trusted)) continue;
      const badge = node('span', 'prep-badge', copy[kind][state] || copy[kind].none); badge.dataset.state = state; row.append(badge);
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
  function dateStatus(race) {
    const official = race.date_status === 'official' && race.race_date, tag = node('span', 'date-status', official ? 'Date officielle' : 'Date à confirmer');
    tag.dataset.state = official ? 'official' : 'unverified'; return tag;
  }
  function raceWhen(race) {
    const when = node('div', 'race-when'), left = node('div');
    left.append(node('p', 'race-date', date(race.race_date)), dateStatus(race));
    when.append(left); const days = countdown(race); if (days) when.append(node('p', 'countdown', days));
    return when;
  }
  function candidates(items) {
    const grid = node('div', 'candidates');
    for (const race of items) {
      const card = node('article', 'candidate'), top = node('div', 'candidate-top'), days = countdown(race);
      top.append(bigDistance(race)); if (days) top.append(node('span', 'countdown', days));
      const where = node('p', 'location'), countryFlag = flag(race); if (countryFlag) where.append(countryFlag);
      where.append(node('span', '', place(race)));
      const tiles = node('dl', 'race-tiles'), when = node('div', 'tile tile-date');
      when.append(node('dt', '', t('Date', 'Date')), node('dd', '', date(race.race_date)), dateStatus(race)); tiles.append(when);
      for (const stat of [...(raceStats(race)?.children || [])]) { stat.className = 'tile'; tiles.append(stat); }
      card.append(top, node('h3', '', race.name || 'Course proposée'), where, tiles);
      for (const extra of [prepBadges(race), sources(race), accessWarning(race)]) if (extra) card.append(extra);
      grid.append(card);
    }
    return grid;
  }
  const uncoveredKinds = race => kinds.filter(kind => ['none', 'closed', 'sold_out', 'not_open'].includes(prepState(race?.preparation?.[kind])));
  const missionSynthetic = () => (mission?.mode || $('mode').value) !== 'live';
  function ctaLabel(count) {
    if (count >= 3) return translate('Confirmer le plan et lancer les 3 agents ↗');
    if (count === 2) return t('Confirmer et lancer les 2 agents disponibles ↗', 'Confirm and launch the 2 available agents ↗');
    if (count === 1) return t('Confirmer et lancer l’agent disponible ↗', 'Confirm and launch the available agent ↗');
    return t('Confirmer le plan · à préparer vous-même ↗', 'Confirm plan · prepare it yourself ↗');
  }
  function coverageNote(race) {
    const missing = uncoveredKinds(race), names = agentNames(), ready = 3 - missing.length;
    const note = node('p', 'plan-coverage'); note.dataset.covered = String(ready);
    if (!missing.length) { note.textContent = t('3 agents prêts à partir en parallèle.', '3 agents ready to start in parallel.'); return note; }
    const list = missing.map(kind => names[kind]).join(t(' et ', ' and '));
    note.textContent = ready ? t(`${ready} agent${ready > 1 ? 's' : ''} prêt${ready > 1 ? 's' : ''} à partir · ${list} : pas encore de site couvert, à préparer vous-même.`, `${ready} agent${ready > 1 ? 's' : ''} ready to start · ${list}: no covered site yet, to prepare yourself.`)
      : t('Aucun site couvert pour ce voyage : à préparer vous-même.', 'No covered site for this trip: prepare it yourself.');
    return note;
  }
  const profileFields = () => [['full_name', 'Nom complet', 'text', 'name', true], ['email', 'E-mail', 'email', 'email', true], ['phone', 'Téléphone', 'tel', 'tel', true],
    ['birth_date', 'Date de naissance', 'date', 'bday', true], ['gender', 'Genre', 'select', 'sex', true], ['nationality', 'Nationalité', 'text', 'country', true], ['address_line', 'Adresse (optionnelle)', 'text', 'street-address', false]];
  const testProfile = {full_name: 'Test Runner', email: 'test.runner@example.com', phone: '+33 6 00 00 00 00', birth_date: '1990-01-01', gender: 'F', nationality: 'FR', address_line: '1 rue de Test, 75001 Paris'};
  let profile = {mission: null, state: 'open'};
  function profileStatusFields(result) {
    const raw = result?.profile_status ?? result?.mission?.profile_status, known = profileFields().map(([key]) => key);
    const list = Array.isArray(raw) ? raw : Array.isArray(raw?.fields) ? raw.fields : Array.isArray(raw?.provided) ? raw.provided
      : raw && typeof raw === 'object' ? Object.entries(raw).filter(([, value]) => value === true || value === 'provided' || value === 'set').map(([key]) => key) : [];
    return known.filter(key => list.includes(key));
  }
  function profileDone(card, fields) {
    const labels = Object.fromEntries(profileFields().map(([key, label]) => [key, label.replace(/ \(optionnelle\)$/, '')]));
    const head = node('div', 'profile-head'), title = node('div'), list = node('ul', 'profile-checks');
    head.append(node('span', 'profile-icon', '✓'), title);
    title.append(node('p', 'eyebrow', t('PROFIL COUREUR', 'RUNNER PROFILE')), node('h3', '', t('Profil prêt pour cette mission', 'Profile ready for this mission')));
    for (const key of fields) list.append(node('li', '', `${translate(labels[key])} ✓`));
    card.dataset.state = 'done';
    card.replaceChildren(head, ...(fields.length ? [list] : []), node('p', 'profile-privacy', t('Gardé en mémoire pour cette mission uniquement, jamais enregistré. Les agents s’arrêtent toujours avant paiement.', 'Kept in memory for this mission only, never stored. Agents always stop before payment.')));
  }
  function profileCard() {
    const card = node('section', 'profile-card'), head = node('div', 'profile-head'), title = node('div'), grid = node('div', 'profile-grid'), inputs = {};
    card.dataset.testid = 'profile-card'; card.dataset.state = 'open'; card.setAttribute('aria-label', t('Profil coureur', 'Runner profile'));
    title.append(node('p', 'eyebrow', 'PROFIL COUREUR · UNE SEULE FOIS'), node('h3', '', 'Vos infos, saisies pour vous'));
    head.append(node('span', 'profile-icon', '◎'), title);
    for (const [key, label, type, autocomplete, required] of profileFields()) {
      const field = node('label', `profile-field${key === 'address_line' ? ' wide' : ''}`), input = document.createElement(type === 'select' ? 'select' : 'input');
      input.className = 'profile-input'; input.dataset.field = key; input.setAttribute('autocomplete', autocomplete); input.setAttribute('spellcheck', 'false');
      if (type === 'select') for (const [value, text] of [['', 'Choisir'], ['F', 'Femme'], ['M', 'Homme'], ['X', 'Non précisé']]) { const option = node('option', '', text); option.value = value; input.append(option); }
      else input.type = type;
      if (required) input.setAttribute('aria-required', 'true');
      inputs[key] = input; field.append(node('span', 'profile-label', label), input); grid.append(field);
    }
    const status = node('p', 'profile-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
    const actions = node('div', 'profile-actions'), fill = node('button', 'profile-fill', 'Remplir avec un profil de test'), skip = node('button', 'profile-skip', 'Continuer sans profil'), save = node('button', 'profile-save', 'Enregistrer pour cette mission ↗');
    for (const button of [fill, skip, save]) button.type = 'button';
    fill.onclick = () => { for (const [key, value] of Object.entries(testProfile)) inputs[key].value = value; status.textContent = t('Profil de test fictif · aucune donnée réelle.', 'Fictional test profile · no real data.'); };
    skip.onclick = () => {
      for (const input of Object.values(inputs)) input.value = '';
      profile.state = 'skipped'; card.dataset.state = 'skipped';
      card.replaceChildren(node('p', 'profile-skipped', t('Sans profil : les agents s’arrêtent avant les formulaires personnels, vous les remplirez vous-même.', 'No profile: agents stop before personal forms, you will fill them in yourself.')));
    };
    save.onclick = async () => {
      if (save.disabled || !mission?.id) return;
      const body = {}, missing = [];
      for (const [key, , type, , required] of profileFields()) {
        const value = String(inputs[key].value ?? '').trim(), invalid = (required && !value) || (type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
        inputs[key].setAttribute('aria-invalid', String(invalid)); if (invalid) missing.push(key); if (value) body[key] = value;
      }
      if (missing.length) { status.dataset.tone = 'error'; status.textContent = t('Complétez les champs requis, ou continuez sans profil.', 'Complete the required fields, or continue without a profile.'); return; }
      const id = mission.id; save.disabled = true; status.dataset.tone = ''; status.textContent = t('Transmission sécurisée…', 'Sending securely…');
      try {
        const result = await api(`/api/missions/${encodeURIComponent(id)}/profile`, body);
        if (mission?.id !== id) return;
        for (const input of Object.values(inputs)) input.value = '';
        profile.state = 'done'; profileDone(card, profileStatusFields(result));
      } catch (err) {
        if ([404, 501].includes(err?.status)) { for (const input of Object.values(inputs)) input.value = ''; profile.state = 'unavailable'; card.remove(); return; }
        save.disabled = false; status.dataset.tone = 'error';
        if (err?.status === 422) {
          const fields = Array.isArray(err.detail) ? err.detail : [];
          const labels = profileFields().filter(([key]) => fields.some(item => item.loc?.includes(key)));
          for (const [key] of labels) inputs[key].setAttribute('aria-invalid', 'true');
          status.textContent = labels.length ? labels.map(([, label]) => `${translate(label)} : ${t('vérifiez ce champ.', 'please check this field.')}`).join(' ') : t('Vérifiez les champs du profil, puis réessayez.', 'Check the profile fields, then try again.');
        } else status.textContent = t('Profil non transmis. Réessayez ou continuez sans profil.', 'Profile not sent. Try again or continue without a profile.');
      }
    };
    actions.append(fill, skip, save);
    card.append(head, node('p', 'profile-copy', 'Les agents tapent ces informations dans les formulaires participant, voyageur et client pour aller le plus loin possible.'), grid,
      node('p', 'profile-privacy', 'Gardé en mémoire pour cette mission uniquement, saisi par les agents dans les formulaires, jamais enregistré. Aucun paiement, compte ni consentement.'), actions, status);
    return card;
  }
  function placeholder() {
    const copy = mission?.plan ? 'Modifier le plan… (ex. départ de Lyon, 3 nuits)' : mission?.candidates?.length ? 'Choisissez une course ou précisez votre envie…' : 'Quelle course vous fait envie ?';
    $('message').setAttribute('data-i18n-placeholder', copy); $('message').setAttribute('placeholder', translate(copy));
  }
  function planCard(p, ready) {
    const card = node('section', 'plan-card'), head = node('div', 'plan-head');
    const where = node('p', 'location'), countryFlag = flag(p.race); if (countryFlag) where.append(countryFlag);
    where.append(node('span', '', [place(p.race), distance(p.race)].filter(Boolean).join(' · ')));
    head.append(node('p', 'eyebrow', 'VOTRE LIGNE DE DÉPART'), node('h3', '', p.race.name), where, raceWhen(p.race), sources(p.race));
    const prep = prepBadges(p.race); if (prep) head.append(prep);
    card.append(head);
    if (p.origin_city || p.race.city) {
      const route = node('div', 'route'), from = node('div', 'route-end'), to = node('div', 'route-end to');
      from.append(node('span', 'route-label', 'Départ'), p.origin_city ? node('strong', '', cityName(p.origin_city)) : node('span', 'route-placeholder', t('Origine à choisir', 'Origin to choose')), node('span', 'route-date', p.arrival_date ? date(p.arrival_date) : ''));
      to.append(node('span', 'route-label', 'Course'), node('strong', '', cityName(p.race.city) || p.race.name), node('span', 'route-date', p.departure_date ? `${t('Retour', 'Return')} ${date(p.departure_date)}` : ''));
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
    const names = agentNames(), missing = uncoveredKinds(p.race);
    for (const kind of kinds) {
      const site = prepSite(p.race.preparation?.[kind]) || (kind === 'registration' ? domainOf(p.race.registration_url || p.race.official_url) : ''), covered = !missing.includes(kind);
      const item = node('li'); item.dataset.covered = String(covered);
      item.append(node('span', 'agent-icon', covered ? agentIcons[kind] : '–'), node('strong', '', names[kind]), node('span', '', covered ? site || t('site choisi au lancement', 'site picked at launch') : t('non couvert · à faire vous-même', 'not covered · do it yourself')));
      crew.append(item);
    }
    card.append(crew, coverageNote(p.race), node('p', 'plan-note', 'Départ, nuits et budget : préférences modifiables, pas des disponibilités réservées.'));
    const warning = accessWarning(p.race, true); if (warning) card.append(warning);
    const site = link(p.race.registration_url || p.race.official_url, 'Voir l’inscription officielle ↗', 'site-link'); if (site) card.append(site);
    if (ready) {
      const area = node('div', 'confirm-area'), button = node('button', 'confirm', ctaLabel(3 - missing.length));
      button.type = 'button'; button.dataset.agents = String(3 - missing.length); button.onclick = () => confirm(button);
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
    const generic = turn.ready_to_confirm && turn.plan && /point de départ|ça (?:te|vous) va|starting point|sound good|does (?:this|that) work/i.test(turn.question);
    if (turn.question) reply.inner.append(node('p', 'question', generic ? t('Tout est bon ? Lancez les agents, ou modifiez un détail ci-dessous.', 'All good? Launch the agents, or tweak a detail below.') : turn.question));
    const chips = node('div', 'chips'); chips.dataset.testid = 'chips'; chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', t('Suggestions de réponse', 'Suggested replies'));
    for (const suggestion of turn.suggestions) {
      if (!suggestion.id || !suggestion.label || suggestion.kind === 'confirm') continue;
      const race = suggestion.kind === 'choose_race' ? turn.candidates.find(r => r.id === suggestion.value || suggestion.id === `choose_race:${r.id}`) : null;
      const monthLabel = String(suggestion.label).replace(/\b(\d{4})-(0[1-9]|1[0-2])\b/g, (_, year, month) => {
        const label = new Intl.DateTimeFormat(locale(), {month: 'long', year: 'numeric', timeZone: 'UTC'}).format(new Date(`${year}-${month}-01T00:00:00Z`));
        return label[0].toUpperCase() + label.slice(1);
      });
      const item = node('div', 'suggestion'), button = node('button', 'chip', `${race?.name || monthLabel} ↗`);
      button.type = 'button'; button.onclick = () => send({suggestion_id: suggestion.id}, suggestion.label);
      if (race && missionSynthetic()) item.append(node('span', 'synthetic-badge', 'Synthétique'));
      const metadata = race ? `${distance(race)} · ${date(race.race_date)}` : {source: 'Course sourcée', synthetic: 'Exemple synthétique', suggested_default: 'Suggestion · modifiable'}[suggestion.provenance] || 'Choisir cette réponse';
      const hint = node('span', 'suggestion-meta', metadata); hint.id = `suggestion-${generation}-${$('thread').querySelectorAll('.message').length}-${chips.children.length}`;
      button.setAttribute('aria-describedby', hint.id); item.append(button, hint); chips.append(item);
    }
    if (chips.children.length) reply.inner.append(chips);
    if (profile.mission !== turn.id) profile = {mission: turn.id, state: 'open'};
    if (turn.ready_to_confirm && turn.plan && profile.state === 'open') reply.inner.append(document.querySelector('.profile-card[data-state="open"]') || profileCard());
    const area = reply.inner.querySelector('.confirm-area'); if (area) reply.inner.append(area);
    placeholder(); localize(); badge(); scroll();
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
      const stage = elapsed < 8 ? t('Recherche des courses officielles', 'Finding official races') : elapsed < 20 ? t('Vérification des dates et distances', 'Checking dates and distances') : t('Comparaison des sources · encore un instant', 'Comparing sources · a little longer');
      progress.textContent = `${stage} · ${t(`${elapsed} s écoulées`, `${elapsed} s elapsed`)}`;
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
      mission.ready_to_confirm = false; document.querySelectorAll('.confirm-area,.chips,.profile-card[data-state="open"]').forEach(el => el.remove());
      const skipped = uncoveredKinds(mission.plan?.race);
      $('agents').hidden = false; $('workspace').classList.add('executing');
      $('history-toggle').hidden = false; $('history-toggle').setAttribute('aria-expanded', 'false');
      kinds.forEach(kind => { agentState[kind] ||= {status: 'pending', level: -1, frames: 0, progress: 0}; agentState[kind].uncovered = skipped.includes(kind); event({kind, type: 'step_started'}); });
      consume(result); poll(token);
    } catch (err) { if (token === generation) { error(err); button.textContent = translate('Réessayer la confirmation'); } }
    finally { if (token === generation) loading(false); }
  }
  const cardFor = kind => document.querySelector(`[data-agent="${kind}"]`);
  const FRESH_MS = 15000;
  const duration = seconds => seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${String(seconds % 60).padStart(2, '0')}`;
  const stageLabels = () => [t('Démarrage', 'Starting'), t('Sur le site', 'On the site'), t('Sélection', 'Selecting')];
  const activityCodes = [[/navigateur disponible|file d.attente|queued|waiting for (?:a )?(?:free )?browser|browser slot/i, 'queued'],
    [/autre site|alternativ|another site|fallback/i, 'alternative'], [/ouverture|opening/i, 'opening'],
    [/navigation|browsing|reviewing|parcour/i, 'browsing'], [/handoff|relais/i, 'handoff']];
  function activityOf(e) {
    const message = String(e.message ?? ''), step = Number.isInteger(e.step) && e.step > 0 ? e.step : Number(/(?:étape|step)\s*(\d{1,3})\b/i.exec(message)?.[1]) || null;
    const code = e.queued === true || e.status === 'queued' ? 'queued' : activityCodes.find(([pattern]) => pattern.test(message))?.[1] || null;
    return code || step ? {code, step} : null;
  }
  function phase(state) {
    if (!state) return 'pending';
    if (state.status === 'ready_for_payment') return 'ready';
    if (terminal.has(state.status)) return 'stopped';
    return state.queued ? 'queued' : state.status === 'running' ? 'working' : 'pending';
  }
  function stepper(kind) {
    const state = agentState[kind], list = cardFor(kind).querySelector('.stepper'); if (!list || !state) return;
    const done = terminal.has(state.status), ready = state.status === 'ready_for_payment';
    const final = ready ? t('Prêt avant paiement', 'Ready before payment') : done ? t('Relais', 'Handover') : t('Avant paiement', 'Before payment');
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
  const frameTime = state => $('mode').value === 'live' ? state.observedTime : state.received;
  const frameAge = state => Number.isFinite(frameTime(state)) ? Math.max(0, Math.floor((Date.now() - frameTime(state)) / 1000)) : null;
  const ageCopy = age => age < 2 ? t('image à l’instant', 'frame just now') : age < 60 ? t(`image il y a ${age} s`, `frame ${age} s ago`)
    : t(`image il y a ${Math.floor(age / 60)} min`, `frame ${Math.floor(age / 60)} min ago`);
  const frozen = state => Boolean(state.image && (state.stale || state.staleFrame || frameAge(state) === null || frameAge(state) >= 60));
  const frozenCopy = age => age === null || age < 60 ? t('IMAGE FIGÉE', 'FROZEN FRAME')
    : t(`IMAGE FIGÉE · il y a ${Math.max(1, Math.floor(age / 60))} min`, `FROZEN FRAME · ${Math.max(1, Math.floor(age / 60))} min ago`);
  function activityLine(kind) {
    const state = agentState[kind], a = state.activity || {};
    if (!terminal.has(state.status) && (state.stale || state.staleFrame || (state.image && (frameAge(state) === null || frameAge(state) >= 60)))) return t('L’agent réfléchit…', 'The agent is thinking…');
    if (terminal.has(state.status)) return state.status === 'ready_for_payment' ? readyTitle(state) : reason(state.reason, state.status, kind, state.active);
    if (state.uncovered && !state.active) return t('Pas de site couvert · à préparer vous-même', 'No covered site · prepare it yourself');
    if (state.queued) return t('En attente d’un navigateur disponible', 'Waiting for a free browser');
    const fallback = state.status === 'running'
      ? {registration: t('Parcours d’inscription officiel', 'Official registration journey'), hotel: t('Recherche de chambre pour vos dates', 'Finding a room for your dates'), transport: t('Recherche de votre aller-retour', 'Finding your return journey')}[kind]
      : t('L’agent se prépare', 'The agent is getting ready');
    const base = state.alternative && a.code !== 'queued' ? t('Essai d’un autre site', 'Trying another site')
      : {opening: t('Ouverture du site', 'Opening the site'), browsing: t('Navigation sur le site', 'Browsing the site'), handoff: t('Préparation du relais', 'Preparing the handover')}[a.code] || fallback;
    return a.step ? `${t(`Étape ${a.step}`, `Step ${a.step}`)} · ${base}` : base;
  }
  const readyTitle = state => state?.prefilled ? t('Formulaire pré-rempli · prêt à payer', 'Form prefilled · ready to pay') : t('Prêt avant paiement', 'Ready before payment');
  function statusLine(kind) {
    const state = agentState[kind], steps = cardFor(kind)?.querySelector('.steps'); if (!state || !steps || terminal.has(state.status)) return;
    const age = state.image ? frameAge(state) : null, line = node('span', 'activity', activityLine(kind));
    line.dataset.phase = phase(state);
    steps.replaceChildren(line, ...(age === null && !frozen(state) ? [] : [node('span', 'frame-age', ` · ${frozen(state) ? frozenCopy(age) : ageCopy(age)}`)]));
  }
  function frameMeta(kind) {
    const state = agentState[kind], card = cardFor(kind); if (!state) return;
    const done = terminal.has(state.status), mode = $('mode').value, age = frameAge(state);
    const stale = frozen(state);
    const interrupted = state.pollFailed || ['failed', 'cancelled'].includes(state.status);
    const synthetic = mode !== 'live';
    const status = !state.image ? '' : interrupted ? t('Image conservée · suivi interrompu', 'Image retained · tracking interrupted')
      : done ? t('Dernière capture · agent arrêté', 'Last screenshot · agent stopped')
      : stale ? frozenCopy(age)
      : age * 1000 >= FRESH_MS ? t('IMAGE RÉCENTE', 'RECENT FRAME')
      : synthetic ? t(`SYNTHÉTIQUE · ${mode === 'replay' ? 'replay' : 'démo'}`, `SYNTHETIC · ${mode === 'replay' ? 'replay' : 'demo'}`) : t('EN DIRECT', 'LIVE');
    const badge = card.querySelector('.live-badge');
    if (badge) { badge.textContent = status; badge.hidden = !status; badge.dataset.tone = interrupted || done || stale || age >= 15 ? 'stopped' : synthetic ? 'synthetic' : 'live'; }
    card.dataset.phase = phase(state);
    const preview = card.querySelector('.preview');
    const parked = !done && !state.image && state.uncovered && !state.active;
    preview.dataset.state = state.image ? stale ? 'stale' : 'available' : done ? 'ended' : parked ? 'uncovered' : state.queued ? 'queued' : 'starting';
    card.dataset.alternative = String(Boolean(state.alternative && !done));
    if (state.alternative && !done) preview.dataset.alt = t('Essai d’un autre site…', 'Trying another site…'); else delete preview.dataset.alt;
    const time = state.image ? (mode === 'replay' ? state.recorded : state.observed) : null;
    const clock = time && Number.isFinite(Date.parse(time)) ? `${mode === 'replay' ? t('heure originale', 'original time') : t('observée', 'observed')} ${new Intl.DateTimeFormat(locale(), {hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC'}).format(new Date(time))} UTC` : '';
    const seconds = state.started ? Math.floor(((state.ended || Date.now()) - state.started) / 1000) : 0;
    const elapsed = done && !state.active ? t('Non démarré', 'Not started') : !state.started ? '' : done ? seconds < 1 ? t('Terminé', 'Finished') : t(`Terminé en ${duration(seconds)}`, `Finished in ${duration(seconds)}`) : seconds > 0 ? t(`Durée ${duration(seconds)}`, `Elapsed ${duration(seconds)}`) : '';
    const meta = [!state.image && !done && !parked ? state.queued ? t('En file d’attente', 'Queued') : t('En attente de la première capture', 'Waiting for the first screenshot') : '', clock, parked ? '' : elapsed].filter(Boolean).join(' · ');
    card.querySelector('.frame-meta').textContent = meta;
    if (!state.image && done) {
      const box = node('div', 'terminal-state'), ready = state.status === 'ready_for_payment', uncovered = !state.active && (state.uncovered || coverageReasons.has(state.reason));
      box.dataset.tone = ready ? 'ready' : state.active ? 'handover' : 'coverage';
      box.append(node('span', 'terminal-icon', ready ? '✓' : state.active || !uncovered ? '↗' : '–'),
        node('strong', '', ready ? readyTitle(state) : state.active ? t('L’agent vous passe le relais', 'The agent hands over to you') : uncovered ? t('Pas de site couvert pour ce trajet', 'No covered site for this trip') : t('Reprise sur le site officiel', 'Continue on the official site')));
      preview.replaceChildren(box);
    } else if (parked) {
      if (!preview.querySelector('.parked')) {
        const box = node('div', 'terminal-state parked'); box.dataset.tone = 'coverage';
        box.append(node('span', 'terminal-icon', '–'), node('strong', '', t('Pas de site couvert pour ce trajet', 'No covered site for this trip')), node('span', 'terminal-sub', t('Détails dans le bilan', 'Details in the summary')));
        preview.replaceChildren(box);
      }
    } else if (!state.image) {
      const copy = state.queued ? t('En attente d’un navigateur disponible…', 'Waiting for a free browser…') : state.alternative ? t('Essai d’un autre site…', 'Trying another site…') : t('Connexion au site…', 'Connecting to the site…');
      if (preview.querySelector('.waiting-copy')?.textContent !== copy) {
        const box = node('div', 'waiting'), skeleton = node('div', 'browser-skeleton'), bar = node('span', 'skeleton-bar'); skeleton.setAttribute('aria-hidden', 'true');
        bar.append(node('b'), node('b'), node('b'), node('em')); skeleton.append(bar, node('i'), node('i'), node('i'));
        box.append(node('span', 'pulse-dot'), node('strong', 'waiting-copy', copy), skeleton, node('span', 'waiting-time')); preview.replaceChildren(box);
      }
      const clockLabel = preview.querySelector('.waiting-time');
      if (clockLabel) clockLabel.textContent = state.started ? t(`${duration(seconds)} écoulées`, `${duration(seconds)} elapsed`) : '';
    }
    statusLine(kind);
  }
  function showFrame(kind, img) {
    const state = agentState[kind], preview = cardFor(kind).querySelector('.preview'), previous = preview.querySelector('img:not(.previous-frame)') || preview.querySelector('img');
    state.image = img; state.stale = false; state.received = Date.now();
    clearTimeout(state.freshTimer);
    const observed = Date.parse(state.observed);
    state.observedTime = Number.isFinite(observed) && observed <= Date.now() ? observed : null;
    const remaining = FRESH_MS - (Date.now() - frameTime(state));
    const ageTick = () => { if (agentState[kind] !== state || terminal.has(state.status)) return; frameMeta(kind); state.freshTimer = setTimeout(ageTick, 15000); };
    if (!terminal.has(state.status)) state.freshTimer = setTimeout(ageTick, Math.max(1, remaining));
    img.className = previous ? 'frame' : 'frame first-frame';
    preview.replaceChildren(img);
    if (previous && previous !== img) {
      previous.className = 'previous-frame'; previous.alt = ''; preview.append(previous);
      const drop = () => previous.remove(); previous.onanimationend = drop; setTimeout(drop, 700);
    }
    frameMeta(kind);
  }
  function loadFrame(kind, e) {
    if (typeof e.frame_id !== 'string' || !/^[a-zA-Z0-9_-]{1,160}$/.test(e.frame_id)) return;
    const state = agentState[kind], token = generation;
    if (state.requested === e.frame_id) return;
    state.requested = e.frame_id;
    const version = state.version = (state.version || 0) + 1;
    const img = new Image(); img.alt = `${$('mode').value === 'live' ? t('Navigateur de l’agent', 'Agent browser') : t('Illustration SYNTHÉTIQUE', 'SYNTHETIC illustration')} · ${agentNames()[kind]}`; img.referrerPolicy = 'no-referrer';
    const current = () => token === generation && agentState[kind] === state && version === state.version;
    const fail = () => { if (current()) { state.stale = true; frameMeta(kind); } };
    img.onerror = fail;
    img.onload = async () => {
      try {
        if (img.decode) await img.decode(); if (!current()) return;
        state.observed = e.observed_at; state.recorded = e.recorded_at; showFrame(kind, img);
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
    const head = node('div', 'success-head'); head.append(check, node('strong', '', readyTitle(state)));
    box.dataset.prefilled = String(Boolean(state.prefilled)); box.append(head);
    if (state.stopLabel) box.append(node('p', 'success-stop', state.stopLabel));
    if (facts.length) box.append(node('p', 'success-facts', facts.join(' · ')));
    box.append(bilan(state));
    const cta = link(state.handoff, t(`Prêt à payer · Continuer sur ${domain} ↗`, `Ready to pay · Continue on ${domain} ↗`), 'handoff-link cta');
    if (cta) box.append(cta);
    if ($('mode').value !== 'live') box.append(node('p', 'success-note', t('Démo synthétique : page d’accueil publique, aucun panier réel.', 'Synthetic demo: public homepage, no real checkout.')));
    return box;
  }
  function bilan(state) {
    const box = node('section', 'bilan'), list = node('ol', 'milestones');
    const ready = state.status === 'ready_for_payment';
    const payment = (ready && $('mode').value === 'live' && state.synthetic !== true) || state.checkpoint === 'payment' || /(?:page de paiement|payment page)/i.test(state.stopLabel || '');
    const reached = payment ? 4 : state.prefilled ? 3 : ready || state.checkpoint === 'selection' ? 2 : state.checkpoint === 'dates' ? 1 : state.active || state.image ? 0 : -1;
    const names = [t('Site ouvert', 'Site opened'), t('Dates', 'Dates'), t('Sélection', 'Selection'), t('Formulaire pré-rempli', 'Form prefilled'), t('Page de paiement', 'Payment page')];
    const head = node('div', 'bilan-head');
    head.append(node('strong', 'bilan-title', t('BILAN', 'ACTIVITY')), node('span', 'bilan-stat', t(`${reached + 1}/5 étapes`, `${reached + 1}/5 steps`)));
    box.append(head);
    for (const [index, label] of names.entries()) {
      const step = node('li', '', label);
      const skipped = payment && index === 3 && !state.prefilled;
      step.dataset.done = String(index <= reached && (index !== 3 || Boolean(state.prefilled)));
      step.dataset.skipped = String(skipped);
      if (skipped) { step.append(node('span', 'milestone-skip', t('non requis', 'not required'))); step.setAttribute('title', t('Pré-remplissage non requis pour atteindre cette page', 'Prefill not required to reach this page')); }
      list.append(step);
    }
    box.append(list);
    if (!ready) box.append(node('p', 'resume-step', `${t('À reprendre ici', 'Resume here')} · ${names[reached] || t('Avant ouverture du site', 'Before opening the site')}`));
    return box;
  }
  function render(kind) {
    const state = agentState[kind], card = cardFor(kind); if (!state || !card) return;
    if (card.dataset.status !== state.status && !globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches) card.animate?.([{opacity: .72, transform: 'translateY(5px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 260, easing: 'ease-out'});
    card.dataset.status = state.status; card.dataset.phase = phase(state);
    card.dataset.tone = ['not_yet_bookable', 'registration_closed', 'sold_out', 'no_site_coverage'].includes(state.reason) ? 'calm' : '';
    const pill = card.querySelector('.status'), key = state.queued && !terminal.has(state.status) ? 'queued' : state.status;
    pill.dataset.status = key; pill.textContent = translate(labels[key] || labels.pending);
    const heading = card.querySelector('h3'); if (heading) heading.textContent = agentNames()[kind];
    const site = card.querySelector('.site');
    if (site) site.textContent = state.site ? `${state.alternative && !terminal.has(state.status) ? t('Autre site · ', 'Alternative · ') : ''}${state.site}` : terminal.has(state.status) && !state.active ? t('Lien officiel', 'Official link') : state.uncovered ? t('Non couvert', 'Not covered') : t('Site choisi au lancement', 'Site picked at launch');
    stepper(kind);
    const steps = card.querySelector('.steps'), handoff = card.querySelector('.handoff');
    if (state.status === 'ready_for_payment' && state.prefilled) steps.textContent = t('Vos informations sont saisies : vérifiez, puis payez vous-même.', 'Your details are typed in: review, then pay yourself.');
    else if (state.status === 'ready_for_payment') steps.textContent = kind === 'registration' ? t('Prêt : vous complétez vous-même l’inscription, puis payez.', 'Ready: you complete the registration details yourself, then pay.') : t('Tout est prêt : il ne reste que le paiement, par vous.', 'All set: only the payment is left, for you.');
    else if (terminal.has(state.status)) {
      const [title, next] = reasonCopy(state.reason, state.status, kind, state.active);
      steps.replaceChildren(node('strong', 'reason-title', title), ...(next ? [node('span', 'reason-next', next)] : []));
    } else statusLine(kind);
    if (state.status === 'ready_for_payment') handoff.replaceChildren(successBox(kind, state));
    else {
      handoff.replaceChildren();
      const domain = domainOf(state.handoff), next = link(state.handoff, state.reason === 'not_yet_bookable' ? t(`Voir les horaires sur ${domain} ↗`, `View timetable on ${domain} ↗`) : t(`Continuer sur ${domain} ↗`, `Continue on ${domain} ↗`), 'handoff-link');
      if (terminal.has(state.status)) {
        const icons = {not_yet_bookable: '◷', registration_closed: '◌', sold_out: '◇', no_site_coverage: '⌁'};
        if (icons[state.reason]) handoff.append(node('span', 'preflight-icon', icons[state.reason]));
        handoff.append(bilan(state));
      }
      if (next) handoff.append(next);
      else if (state.site || state.started || state.active) handoff.append(node('p', 'site-footer', state.site || t('Site en cours d’ouverture', 'Opening the site')));
      else if (terminal.has(state.status)) handoff.append(node('p', 'no-site', t('Pas de site vérifié pour cette étape', 'No verified site for this step')));
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
  function liveStrip(states) {
    const race = tripFacts().race, recap = document.querySelector('.mission-recap'), count = document.querySelector('.live-count');
    if (recap) recap.textContent = race?.name ? [clean(race.name), date(race.race_date), [tripFacts().origin_city && cityName(tripFacts().origin_city), cityName(race.city)].filter(Boolean).join(' → ')].filter(Boolean).join(' · ') : '';
    if (!count) return;
    const tally = [[t('En action', 'Working'), states.filter(s => s && !terminal.has(s.status)).length, 'working'],
      [t('Prêts', 'Ready'), states.filter(s => s?.status === 'ready_for_payment').length, 'ready'],
      [t('Relais', 'Handover'), states.filter(s => s && terminal.has(s.status) && s.status !== 'ready_for_payment').length, 'stopped']];
    count.replaceChildren(...tally.map(([label, value, tone]) => { const item = node('div'); item.dataset.tone = tone; item.append(node('dt', '', label), node('dd', '', `${value}/3`)); return item; }));
  }
  function summaryCard(dead, ready) {
    const names = agentNames(), list = node('ul', 'summary-list'), coverage = $('coverage');
    for (const kind of kinds) {
      const state = agentState[kind], ok = state.status === 'ready_for_payment', item = node('li'), body = node('div', 'summary-body');
      const [title, next] = ok ? [readyTitle(state), t('Il ne reste que vos informations et le paiement, par vous.', 'Only your details and the payment are left, for you.')] : reasonCopy(state.reason, state.status, kind, state.active);
      const preflight = !state.active && !state.frames && ['not_yet_bookable', 'registration_closed', 'sold_out', 'no_site_coverage'].includes(state.reason);
      item.dataset.status = ok ? 'ready' : preflight ? 'preflight' : 'stopped';
      body.append(node('strong', '', names[kind]), node('span', 'summary-reason', title), ...(next ? [node('span', 'summary-next', next)] : []));
      const domain = domainOf(state.handoff), go = link(state.handoff, ok ? t(`Payer sur ${domain} ↗`, `Pay on ${domain} ↗`) : t(`Continuer sur ${domain} ↗`, `Continue on ${domain} ↗`), 'summary-link');
      item.append(node('span', 'agent-icon', ok ? '✓' : agentIcons[kind]), body, go || node('span', 'summary-none', t('Pas de site vérifié', 'No verified site')));
      list.append(item);
    }
    const chips = node('div', 'chips coverage-chips');
    for (const [label, text] of changeChips()) {
      const item = node('div', 'suggestion'), button = node('button', 'chip', `${label} ↗`);
      button.type = 'button'; button.onclick = () => restart(text);
      item.append(button, node('span', 'suggestion-meta', text)); chips.append(item);
    }
    coverage.dataset.tone = dead ? 'coverage' : ready ? 'partial' : 'handover';
    const title = dead ? t('Ce voyage n’est pas encore couvert par nos agents', 'Our agents do not cover this trip yet')
      : ready ? t(`${ready}/3 prêt${ready > 1 ? 's' : ''} avant paiement`, `${ready}/3 ready before payment`) : t('Vos agents vous passent le relais', 'Your agents hand over to you');
    const copy = dead ? t('Aucun agent n’a pu démarrer : nos sites vérifiés ne couvrent pas encore cette course, cette ville ou ce départ. Rien n’a été réservé ni envoyé.', 'No agent could start: our reviewed sites do not cover this race, city or origin yet. Nothing was booked or sent.')
      : ready ? t('Une partie est prête. Reprenez le reste en un clic sur les sites indiqués : rien n’a été réservé, payé ni envoyé.', 'Part of the trip is ready. Pick up the rest in one click on the sites below: nothing was booked, paid or sent.')
      : t('Cette fois, aucune étape n’est allée jusqu’au paiement. Rien n’a été réservé, payé ni envoyé : voici où reprendre, en un clic.', 'This time no step reached payment. Nothing was booked, paid or sent: here is where to pick up, in one click.');
    const head = node('div', 'summary-head'), heading = node('div');
    head.append(node('span', 'coverage-icon', dead ? '↺' : ready ? '✓' : '↗'), heading);
    heading.append(node('p', 'eyebrow', dead ? t('COUVERTURE', 'COVERAGE') : t('BILAN DE LA PRÉPARATION', 'PREPARATION SUMMARY')), node('h3', '', title));
    coverage.replaceChildren(head, node('p', 'coverage-copy', copy), list, node('p', 'question', t('On essaie autre chose ?', 'Shall we try something else?')), chips);
  }
  function overview() {
    const states = kinds.map(kind => agentState[kind]), finished = states.every(state => state && terminal.has(state.status));
    const ready = states.filter(state => state?.status === 'ready_for_payment').length, banner = $('mission-banner'), coverage = $('coverage');
    const dead = finished && !ready && states.every(state => !state.active && coverageReasons.has(state.reason));
    $('agents').dataset.view = dead ? 'coverage' : finished && ready < 3 ? 'summary' : 'agents';
    $('agents').dataset.finished = String(finished);
    liveStrip(states);
    banner.hidden = !(finished && ready === 3);
    if (!banner.hidden && banner.dataset.rendered !== language) {
      banner.dataset.rendered = language; banner.dataset.tone = 'success';
      const race = tripFacts().race?.name;
      banner.replaceChildren(node('span', 'banner-check', '✓'), node('strong', '', t('3/3 · Tout est prêt avant paiement', '3/3 · Everything is ready before payment')),
        node('span', '', race ? t(`${race} : dossard, hôtel et trajet vous attendent. Vous complétez vos informations et payez vous-même, sur chaque site.`, `${race}: bib, hotel and journey are waiting. You enter your details and pay yourself, on each site.`)
          : t('Les trois étapes vous attendent : vous complétez vos informations et payez vous-même, sur chaque site.', 'All three steps are waiting: you enter your details and pay yourself, on each site.')));
    }
    coverage.hidden = !(finished && ready < 3);
    if (coverage.hidden) return;
    const signature = `${language}|${dead}|${states.map(state => `${state.status}:${state.reason}:${state.handoff}:${state.active}`).join('|')}`;
    if (coverage.dataset.rendered === signature) return;
    coverage.dataset.rendered = signature; summaryCard(dead, ready);
  }
  function focusAgent(kind) {
    const agents = $('agents'), next = kinds.includes(kind) && agents.dataset.focus !== kind ? kind : '';
    if (next) agents.dataset.focus = next; else delete agents.dataset.focus;
    for (const name of kinds) {
      const card = cardFor(name), on = name === next, button = card?.querySelector('.focus-toggle'); if (!card) continue;
      card.dataset.focused = String(on);
      if (button) { button.setAttribute('aria-pressed', String(on)); button.setAttribute('aria-label', on ? t('Revenir aux trois agents', 'Back to all three agents') : `${t('Agrandir l’agent', 'Enlarge agent')} ${agentNames()[name]}`); button.textContent = on ? '✕' : '⤢'; }
    }
    return next || null;
  }
  function event(raw) {
    const e = {...raw, ...raw.data}; if (Number.isFinite(Number(e.sequence))) after = Math.max(after, Number(e.sequence));
    if (!kinds.includes(e.kind)) return;
    const state = agentState[e.kind] ||= {status: 'pending', level: -1, frames: 0, progress: 0};
    if (typeof e.stale_frame === 'boolean') state.staleFrame = e.stale_frame;
    if (e.prefilled === true) state.prefilled = true;
    if (typeof e.synthetic === 'boolean') state.synthetic = e.synthetic;
    if (['dates', 'selection', 'payment'].includes(e.checkpoint)) state.checkpoint = e.checkpoint;
    const message = String(e.message ?? ''), activity = e.type === 'step_progress' || e.status === 'queued' ? activityOf(e) : null;
    if (e.type === 'step_started') { state.started ||= Date.now(); state.level = Math.max(state.level, 0); }
    if (activity?.code === 'queued') { state.queued = true; state.started ||= Date.now(); state.level = Math.max(state.level, 0); if (!terminal.has(state.status)) state.status = 'running'; }
    else if (e.type === 'live_frame' || (e.type === 'step_progress' && !/unavailable|size limit/i.test(message))) {
      state.active = true; state.queued = false; state.started ||= Date.now();
      if (e.type === 'live_frame') state.frames++; else state.progress++;
      state.level = Math.max(state.level, state.frames >= 3 || state.progress >= 3 ? 2 : 1);
    }
    if (activity) state.activity = activity.code === null && state.activity?.code ? {...state.activity, step: activity.step} : activity;
    if (e.type === 'step_progress' && (e.alternative === true || activity?.code === 'alternative')) state.alternative = true;
    if (e.status === 'prefilled') { e.status = 'ready_for_payment'; e.prefilled = true; }
    if (terminal.has(e.status)) state.status = e.status;
    else if (e.type === 'step_started' && !terminal.has(state.status)) state.status = 'running';
    if (terminal.has(state.status)) { state.ended ||= Date.now(); state.queued = false; clearTimeout(state.freshTimer); }
    if (terminal.has(e.status)) {
      state.reason = e.reason_code || (e.checkpoint_reached === true && e.status !== 'ready_for_payment' ? 'checkpoint_reached' : null) || state.reason;
      state.total = shownTotal(e.summary) || state.total; state.alternative = false; state.activity = null;
      if (e.status === 'ready_for_payment') { state.prefilled = e.prefilled === true || state.prefilled === true; state.stopLabel = typeof e.stop_label === 'string' ? clean(e.stop_label).replace(/[{}[\]<>]/g, '').trim().slice(0, 80) : state.stopLabel || ''; }
    }
    const visited = domainOf(e.final_url) || domainOf(e.site_url) || domainOf(e.start_url);
    if (visited) state.site = visited;
    const href = safeURL(e.handoff_url); if (href) state.handoff = href;
    if (!state.site && state.handoff) state.site = domainOf(state.handoff);
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
    for (const kind of kinds) { clearTimeout(agentState[kind]?.freshTimer); delete agentState[kind]; }
    focusAgent(null);
    document.querySelectorAll('.agent').forEach(card => {
      card.dataset.status = 'pending'; card.dataset.phase = 'pending';
      card.querySelector('.preview').textContent = translate('En attente de la première capture'); card.querySelector('.preview').dataset.state = 'unavailable';
      card.querySelector('.frame-meta').textContent = translate('Aucune image reçue'); card.querySelector('.steps').textContent = translate('L’agent se prépare.'); card.querySelector('.handoff').replaceChildren();
      const pill = card.querySelector('.status'); pill.dataset.status = 'pending'; pill.textContent = translate(labels.pending);
      for (const [cls, value] of [['.site', 'Site choisi au lancement'], ['.live-badge', '']]) { const el = card.querySelector(cls); if (el) { el.textContent = translate(value); if (cls === '.live-badge') el.hidden = true; } }
      card.querySelector('.stepper')?.replaceChildren();
    });
    $('mission-banner').hidden = true; $('mission-banner').dataset.rendered = ''; $('coverage').hidden = true; $('coverage').replaceChildren(); $('coverage').dataset.rendered = '';
    $('agents').dataset.view = 'agents'; $('agents').dataset.finished = 'false';
    document.querySelector('.mission-recap')?.replaceChildren(); document.querySelector('.live-count')?.replaceChildren();
    $('agents').hidden = true; $('history-toggle').hidden = true; $('history-toggle').setAttribute('aria-expanded', 'false');
    $('workspace').classList.remove('executing'); $('workspace').classList.remove('history-open');
  }
  function restart(text) {
    generation++; clearTimeout(timer); mission = null; after = 0; loading(false); resetStage(); send({text}, text);
  }
  $('mode').onchange = () => {
    generation++; clearTimeout(timer); mission = null; after = 0; language = globalThis.navigator?.language?.startsWith('en') ? 'en' : 'fr'; loading(false);
    resetStage(); document.querySelectorAll('.message').forEach(el => el.remove());
    $('welcome').hidden = false; $('message').value = ''; $('toast').hidden = true; profile = {mission: null, state: 'open'}; placeholder(); localize(); badge();
  };
  document.querySelectorAll('.agent').forEach(card => {
    const kind = card.dataset.agent, button = card.querySelector('.focus-toggle'), stage = card.querySelector('.stage');
    if (button) button.onclick = e => { e?.stopPropagation?.(); focusAgent(kind); };
    if (stage) stage.onclick = () => { if ($('agents').dataset.focus !== kind) focusAgent(kind); };
  });
  globalThis.addEventListener?.('keydown', e => {
    const current = $('agents').dataset.focus; if (!current || $('agents').hidden) return;
    if (e.key === 'Escape') { focusAgent(null); cardFor(current)?.querySelector('.focus-toggle')?.focus?.(); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const next = kinds[(kinds.indexOf(current) + (e.key === 'ArrowRight' ? 1 : 2)) % 3]; focusAgent(next); cardFor(next)?.querySelector('.focus-toggle')?.focus?.();
    }
  });
  let demoCount = 0;
  function demoFrame(kind) {
    const label = {registration: 'REGISTRATION', hotel: 'HOTEL', transport: 'TRANSPORT'}[kind], shade = ['#1d1d22', '#22222a', '#1a1f24'][demoCount++ % 3];
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><rect width="800" height="500" fill="${shade}"/><rect x="40" y="40" width="${300 + (demoCount % 4) * 100}" height="10" rx="5" fill="#fc4c02"/><text x="40" y="120" fill="#fff" font-family="Arial" font-size="40" font-weight="700">${label}</text><text x="40" y="180" fill="#c9c9d2" font-family="Arial" font-size="24">SYNTHETIC demo screen · not a real site</text><rect x="40" y="230" width="460" height="24" rx="12" fill="#33333b"/><rect x="40" y="280" width="${200 + (demoCount % 3) * 80}" height="24" rx="12" fill="#33333b"/></svg>`;
    const img = new Image(); img.alt = `${t('Illustration SYNTHÉTIQUE', 'SYNTHETIC illustration')} · ${agentNames()[kind]}`;
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    showFrame(kind, img);
  }
  function demoStage(name) {
    if ($('mode').value === 'live') return false;
    const fake = (kind, data) => event({kind, synthetic: true, ...data});
    const show = () => { $('agents').hidden = false; $('workspace').classList.add('executing'); $('history-toggle').hidden = false; };
    if (name === 'stale') kinds.forEach(kind => { const state = agentState[kind]; if (state?.received) { state.received -= 90000; frameMeta(kind); } });
    else if (name === 'alternative') fake('hotel', {type: 'step_progress', message: 'Essai d\'un autre site'});
    else if (name === 'frame') kinds.forEach(kind => { if (agentState[kind] && !terminal.has(agentState[kind].status)) demoFrame(kind); });
    else if (name === 'focus') focusAgent('hotel');
    else {
      resetStage(); show();
      const codes = name === 'coverage' ? ['no_site_coverage', 'no_site_coverage', 'policy_denied'] : ['sold_out', 'no_inventory', 'captcha'];
      kinds.forEach((kind, index) => {
        if (name === 'preflight') {
          fake(kind, {status: 'blocked', reason_code: ['registration_closed', 'sold_out', 'not_yet_bookable'][index], handoff_url: `https://example.com/runai-synthetic/${kind}`});
          return;
        }
        fake(kind, {type: 'step_started'});
        if (name === 'queued') { fake(kind, {type: 'step_progress', message: index === 2 ? 'Ouverture du site' : 'En attente d\'un navigateur disponible'}); return; }
        if (name === 'coverage') { fake(kind, {status: 'blocked', reason_code: codes[index], handoff_url: index ? null : 'https://example.com/runai-synthetic/registration'}); return; }
        fake(kind, {type: 'step_progress', message: 'Ouverture du site', start_url: `https://example.com/runai-synthetic/${kind}`});
        if (name === 'running') { fake(kind, {type: 'step_progress', message: `Étape ${index + 3}`}); demoFrame(kind); return; }
        fake(kind, {type: 'step_progress', message: 'Navigation sur le site'}); fake(kind, {type: 'step_progress', message: 'Étape 6'}); demoFrame(kind);
        const win = name === 'success' || (name === 'partial' && index === 1);
        fake(kind, win ? {status: 'ready_for_payment', summary: kind === 'registration' ? '' : 'SYNTHETIC total 312 €', handoff_url: `https://example.com/runai-synthetic/${kind}`}
          : {status: 'blocked', reason_code: name === 'partial' ? ['policy_denied', null, 'no_inventory'][index] : codes[index], handoff_url: `https://example.com/runai-synthetic/${kind}`});
      });
    }
    return true;
  }
  globalThis.__runai = {event, consume, frameMeta, safeURL, reason, reasonCopy, reasons, flag, detectLanguage: value => { detectLanguage(value); return language; }, demo: demoStage, focus: focusAgent, cityName, translate, setLanguage: value => { language = value; localize(); badge(); }};
  placeholder(); localize(); badge(); const initialGeneration = generation;
  api('/api/health').then(health => {
    liveReady = health.live_ready || null;
    if (generation === initialGeneration && !mission && !busy && ['demo', 'replay', 'live'].includes(health.mode)) $('mode').value = health.mode;
    badge();
  }).catch(() => {});
})();
