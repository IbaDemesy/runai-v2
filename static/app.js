(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const kinds = ['registration', 'hotel', 'transport'];
  const terminal = new Set([
    'ready_for_payment',
    'completed',
    'partial',
    'done',
    'failed',
    'blocked',
    'cancelled'
  ]);
  const labels = {
    pending: 'En attente',
    running: 'En cours',
    ready_for_payment: 'À vous de jouer',
    blocked: 'Bloqué',
    failed: 'Échec'
  };
  let mission = null,
    after = 0,
    timer = null,
    busy = false,
    generation = 0,
    liveReady = null;
  const agentState = {};
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const node = (tag, cls, value) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (value !== undefined) el.textContent = String(value);
    return el;
  };
  const text = value =>
    typeof value === 'string' ? value : value?.text || value?.content || '';
  const safeURL = value => {
    try {
      const url = new URL(value);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
    } catch {
      return null;
    }
  };
  const safeViewURL = value => {
    try {
      const url = new URL(value, location.href);
      return ['http:', 'https:'].includes(url.protocol) &&
        url.origin !== location.origin
        ? url.href
        : null;
    } catch {
      return null;
    }
  };
  function link(url, title, cls) {
    const href = safeURL(url);
    if (!href) return node('span', cls, `${title} · indisponible`);
    const a = node('a', cls, title);
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    return a;
  }
  function normalize(raw) {
    const envelope = raw?.mission || raw || {};
    const data = envelope.turns?.at(-1) || raw?.turn || envelope;
    const plan = data.draft || data.plan || envelope.trip;
    return {
      ...data,
      id: data.mission_id || data.id || envelope.mission_id || envelope.id,
      assistant_message: text(data.assistant_message || data.message),
      question: text(data.question),
      suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
      candidates: Array.isArray(data.candidates || data.options)
        ? data.candidates || data.options
        : [],
      plan: plan && Object.keys(plan).length ? plan : null,
      ready_to_confirm:
        data.ready_to_confirm === true || data.confirmation_required === true
    };
  }
  function scroll() {
    $('thread').scrollTop = $('thread').scrollHeight;
  }
  function badge() {
    $('mode-badge').textContent = {
      demo: 'SIMULATION SYNTHÉTIQUE',
      replay: 'REPLAY · enregistrement synthétique · heure originale',
      live: 'LIVE · agents réels · arrêt avant paiement'
    }[$('mode').value];
    $('mode').title =
      $('mode').value === 'live' &&
      liveReady &&
      (!liveReady.linkup || !liveReady.h)
        ? 'Live indisponible : configuration des services incomplète'
        : 'Choisir le mode';
    $('live-hint').hidden = !(
      $('mode').value === 'live' &&
      liveReady &&
      (!liveReady.linkup || !liveReady.h)
    );
  }
  function error(err) {
    $('toast')
      .querySelectorAll('.chip')
      .forEach(el => el.remove());
    $('toast').hidden = false;
    $('toast').querySelector('p').textContent = err.message;
  }
  async function api(path, body) {
    const response = await fetch(
      path,
      body === undefined
        ? {}
        : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          }
    );
    let data;
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    if (!response.ok) {
      const detail =
        data.detail || data.message || `Erreur serveur (${response.status})`;
      throw Error(
        Array.isArray(detail)
          ? detail.map(item => item.msg || JSON.stringify(item)).join(' · ')
          : typeof detail === 'string'
            ? detail
            : JSON.stringify(detail)
      );
    }
    return data;
  }
  function message(role, content) {
    $('welcome').hidden = true;
    const wrap = node('article', `message ${role}`);
    if (role === 'assistant') wrap.append(node('span', 'avatar', 'R↗'));
    const inner = node('div', 'message-content');
    if (role === 'assistant')
      inner.append(node('div', 'message-name', 'RUNAI · VOTRE COPILOTE'));
    const bubble = node('p', 'bubble', content);
    inner.append(bubble);
    wrap.append(inner);
    $('thread').append(wrap);
    scroll();
    return { wrap, inner, bubble };
  }
  async function reveal(el, value) {
    if (reduced.matches) {
      el.textContent = value;
      scroll();
      return;
    }
    for (let i = 0; i < value.length; i += 7) {
      el.textContent = value.slice(0, i + 7);
      scroll();
      await new Promise(resolve => setTimeout(resolve, 15));
    }
  }
  function provenance(value) {
    return node(
      'span',
      'provenance',
      ['source', 'sourced'].includes(value)
        ? 'Sourcé'
        : value === 'synthetic'
          ? 'Synthétique'
          : value === 'suggested_default'
            ? 'Suggestion · modifiable'
            : 'Source non précisée'
    );
  }
  function candidates(items) {
    const grid = node('div', 'candidates');
    for (const race of items) {
      const card = node('article', 'candidate');
      const distance = node('div', 'distance', race.distance_km ?? '—');
      distance.append(node('small', '', ' km'));
      card.append(
        distance,
        node('h3', '', race.name || race.race || 'Course à préciser'),
        node('p', '', `Édition ${race.edition || 'à préciser'}`)
      );
      card.append(
        node('p', '', race.race_date || race.date || 'Date inconnue'),
        node(
          'span',
          'date-status',
          {
            official: 'Date officielle',
            confirmed: 'Date confirmée',
            to_confirm: 'Date à confirmer',
            unknown: 'Date inconnue'
          }[race.date_status] || 'Date à confirmer'
        )
      );
      const p = node('p');
      p.append(provenance(race.provenance));
      card.append(p, link(race.official_url, 'Site officiel ↗'));
      grid.append(card);
    }
    return grid;
  }
  function planCard(plan, ready) {
    const p = { ...plan.framing, ...plan };
    const card = node('section', 'plan-card');
    const head = node('div', 'plan-head');
    head.append(
      node('p', 'eyebrow', 'VOTRE PLAN DE COURSE'),
      node(
        'h3',
        '',
        (typeof p.race === 'object' ? p.race?.name : p.race) ||
          'Course à préciser'
      ),
      node('span', 'provenance', 'À vérifier avant le départ')
    );
    const facts = node('dl', 'plan-facts');
    for (const [label, value] of [
      ['Course', p.race?.race_date || p.race_date],
      ['Arrivée', p.arrival_date || p.departure],
      ['Retour', p.departure_date || p.return_date],
      ['Départ', p.origin_city],
      ['Nuits', p.nights],
      ['Budget', p.budget_eur != null ? `${p.budget_eur} €` : null]
    ]) {
      const f = node('div', 'fact');
      f.append(node('dt', '', label), node('dd', '', value ?? 'À préciser'));
      facts.append(f);
    }
    const sites = node('div', 'sites');
    for (const kind of kinds) {
      const site = p.sites?.[kind];
      const url =
        (typeof site === 'string' ? site : site?.url) ||
        (kind === 'registration'
          ? p.race?.registration_url || p.race?.official_url
          : null);
      sites.append(
        link(
          url,
          `${{ registration: 'Dossard', hotel: 'Hôtel', transport: 'Transport' }[kind]} ↗`,
          'site-link'
        )
      );
    }
    card.append(head, facts, sites);
    if (ready) {
      const area = node('div', 'confirm-area');
      const button = node(
        'button',
        'confirm',
        'Je confirme le plan · lancer les 3 agents ↗'
      );
      button.type = 'button';
      button.onclick = () => confirm(button);
      area.append(
        node(
          'p',
          '',
          'Confirmez uniquement ce plan. Aucun paiement, consentement ou réservation ne sera effectué.'
        ),
        button
      );
      card.append(area);
    }
    return card;
  }
  async function renderTurn(raw, reply) {
    const turn = normalize(raw);
    mission = { ...mission, ...turn, id: turn.id || mission?.id };
    if (!mission.id)
      throw Error(
        'Réponse incomplète : identifiant de mission manquant. Réessayez.'
      );
    const content =
      [turn.assistant_message, turn.error, turn.question]
        .filter((s, i, a) => s && a.indexOf(s) === i)
        .join('\n\n') ||
      'Aucune proposition pour le moment. Précisez votre envie de course.';
    await reveal(reply.bubble, content);
    if (turn.candidates.length) reply.inner.append(candidates(turn.candidates));
    if (turn.plan)
      reply.inner.append(planCard(turn.plan, turn.ready_to_confirm));
    if (turn.suggestions.length) {
      const chips = node('div', 'chips');
      chips.dataset.testid = 'chips';
      for (const suggestion of turn.suggestions) {
        if (!suggestion.id || !suggestion.label) continue;
        if (suggestion.kind === 'confirm' && !turn.ready_to_confirm) continue;
        const button = node('button', 'chip', suggestion.label);
        button.type = 'button';
        button.append(provenance(suggestion.provenance));
        button.onclick = () =>
          suggestion.kind === 'confirm'
            ? confirm(button)
            : send({ suggestion_id: suggestion.id }, suggestion.label);
        chips.append(button);
      }
      reply.inner.append(chips);
    }
    scroll();
  }
  function loading(value) {
    busy = value;
    $('mode').disabled = value;
    $('send').disabled = value;
    $('send').textContent = value ? '···' : '↑';
    document
      .querySelectorAll('.chip,.example-chips button,.confirm')
      .forEach(b => {
        b.disabled = value;
      });
  }
  async function send(body, label) {
    if (busy) return;
    loading(true);
    $('toast').hidden = true;
    const previousControls = document.querySelectorAll('.chips,.confirm-area');
    message('user', label);
    $('message').value = '';
    $('message').style.height = '';
    const reply = message('assistant', '');
    const typing = node('div', 'typing');
    typing.setAttribute('aria-label', 'RunAI réfléchit');
    for (let i = 0; i < 3; i++) typing.append(node('span'));
    reply.bubble.append(typing);
    try {
      const result = await api(
        mission
          ? `/api/missions/${encodeURIComponent(mission.id)}/messages`
          : '/api/missions',
        mission ? body : { ...body, mode: $('mode').value }
      );
      reply.bubble.replaceChildren();
      await renderTurn(result, reply);
      previousControls.forEach(el => el.remove());
    } catch (err) {
      reply.bubble.textContent =
        'La demande n’a pas abouti. Vous pouvez réessayer.';
      error(err);
    } finally {
      loading(false);
      scroll();
    }
  }
  async function confirm(button) {
    if (busy || !mission?.ready_to_confirm) return;
    loading(true);
    button.textContent = 'Lancement…';
    try {
      const result = await api(
        `/api/missions/${encodeURIComponent(mission.id)}/confirm`,
        { confirmed: true }
      );
      mission.ready_to_confirm = false;
      document
        .querySelectorAll('.confirm-area,.chips')
        .forEach(el => el.remove());
      $('agents').hidden = false;
      $('workspace').classList.add('executing');
      message(
        'assistant',
        'Votre équipe prend le relais. Les trois agents s’arrêtent avant tout paiement ou engagement.'
      );
      consume(result);
      poll(generation);
    } catch (err) {
      error(err);
      button.textContent = 'Réessayer la confirmation';
    } finally {
      loading(false);
    }
  }
  function event(raw) {
    const e = { ...raw, ...raw.data };
    const sequence = Number(e.sequence);
    if (Number.isFinite(sequence)) after = Math.max(after, sequence);
    if (!kinds.includes(e.kind)) return;
    const card = document.querySelector(`[data-agent="${e.kind}"]`);
    const state = (agentState[e.kind] ||= {});
    const status =
      e.status ||
      (e.type === 'step_started'
        ? 'running'
        : e.type === 'step_finished'
          ? state.status
          : null);
    if (status) {
      state.status = status;
      const pill = card.querySelector('.status');
      pill.dataset.status = status;
      pill.textContent = labels[status] || status;
    }
    if (e.message || e.summary || e.error) {
      const line = node(
        'li',
        '',
        [e.message || e.summary, e.error].filter(Boolean).join(' · ')
      );
      if ($('mode').value === 'replay')
        line.append(
          node(
            'time',
            '',
            e.recorded_at
              ? `Heure originale · ${e.recorded_at}`
              : 'Heure originale indisponible'
          )
        );
      const steps = card.querySelector('.steps');
      steps.append(line);
      steps.scrollTop = steps.scrollHeight;
    }
    const view = safeViewURL(e.live_view_url);
    if (e.live_view_url != null && !view && state.view) {
      state.view = null;
      card
        .querySelector('.preview')
        .replaceChildren(node('span', '', 'Aperçu indisponible'));
    }
    if (view && state.view !== view) {
      state.view = view;
      const iframe = node('iframe');
      iframe.src = view;
      iframe.title = `Aperçu ${e.kind}`;
      iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
      iframe.referrerPolicy = 'no-referrer';
      card
        .querySelector('.preview')
        .replaceChildren(iframe, link(view, 'Ouvrir dans un onglet ↗'));
    } else if (e.frame_id && !state.view) {
      const img = node('img');
      img.alt = `${$('mode').value === 'live' ? 'Capture agent' : 'Capture synthétique'} · ${e.observed_at || 'heure indisponible'}`;
      img.src = `/api/frames/${encodeURIComponent(e.frame_id)}`;
      img.onerror = () =>
        card
          .querySelector('.preview')
          .replaceChildren(node('span', '', 'Aperçu indisponible'));
      card.querySelector('.preview').replaceChildren(img);
    }
    if (e.handoff_url)
      card
        .querySelector('.handoff')
        .replaceChildren(
          link(
            e.handoff_url,
            'Continuer sur le site — paiement à faire par vous ↗'
          )
        );
  }
  function consume(raw) {
    const list = Array.isArray(raw) ? raw : raw.events || raw.mission?.events;
    const events = Array.isArray(list) ? list : [];
    for (const e of [...events].sort(
      (a, b) => (a.sequence || 0) - (b.sequence || 0)
    ))
      if (!e.sequence || Number(e.sequence) > after) event(e);
    for (const result of raw.results || []) {
      const state = (agentState[result.kind] ||= {});
      const signature = JSON.stringify(result);
      if (state.result !== signature) {
        state.result = signature;
        event(result);
      }
    }
    return (
      terminal.has(raw.status) ||
      kinds.every(kind => terminal.has(agentState[kind]?.status))
    );
  }
  async function poll(token) {
    if (token !== generation) return;
    try {
      const result = await api(
        `/api/missions/${encodeURIComponent(mission.id)}/events?after=${after}`
      );
      if (token !== generation) return;
      consume(result);
      const snapshot = await api(
        `/api/missions/${encodeURIComponent(mission.id)}`
      );
      if (token !== generation || consume(snapshot)) return;
      timer = setTimeout(() => poll(token), 1000);
    } catch (err) {
      error(err);
      const retry = node('button', 'chip', 'Reprendre le suivi');
      retry.onclick = () => {
        retry.remove();
        $('toast').hidden = true;
        poll(token);
      };
      $('toast').append(retry);
    }
  }
  $('composer').onsubmit = e => {
    e.preventDefault();
    const value = $('message').value.trim();
    if (value) send({ text: value }, value);
  };
  $('message').onkeydown = e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      $('composer').requestSubmit();
    }
  };
  $('message').oninput = () => {
    $('message').style.height = 'auto';
    $('message').style.height = `${Math.min($('message').scrollHeight, 130)}px`;
  };
  document.querySelectorAll('[data-prompt]').forEach(button => {
    button.onclick = () =>
      send({ text: button.dataset.prompt }, button.dataset.prompt);
  });
  $('toast').querySelector('button').onclick = () => {
    $('toast').hidden = true;
  };
  $('mode').onchange = () => {
    generation++;
    clearTimeout(timer);
    mission = null;
    after = 0;
    for (const kind of kinds) delete agentState[kind];
    document.querySelectorAll('.message').forEach(el => el.remove());
    document.querySelectorAll('.agent').forEach(card => {
      card.querySelector('.preview').textContent = 'Aperçu indisponible';
      card.querySelector('.steps').replaceChildren();
      card.querySelector('.handoff').replaceChildren();
      const pill = card.querySelector('.status');
      pill.dataset.status = 'pending';
      pill.textContent = labels.pending;
    });
    $('welcome').hidden = false;
    $('agents').hidden = true;
    $('workspace').classList.remove('executing');
    $('toast').hidden = true;
    badge();
  };
  badge();
  const initialGeneration = generation;
  api('/api/health')
    .then(health => {
      liveReady = health.live_ready || null;
      if (
        generation === initialGeneration &&
        !mission &&
        !busy &&
        ['demo', 'replay', 'live'].includes(health.mode)
      )
        $('mode').value = health.mode;
      badge();
    })
    .catch(() => {
      /* The first request will report service errors if health is unavailable. */
    });
})();
