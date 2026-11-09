import asyncio
import base64
import json
import sys
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from runai.agents import hotel as hotel_builder
from runai.agents import registration as registration_builder
from runai.agents.hclient import (
    GUARDRAILS,
    HAgentRunner,
    HUnavailable,
    _checkpoint,
    _checkpoint_matches,
    _payment_claim,
    _policy,
    _PolicyBlocked,
    _reviewed,
    _verification_failures,
)
from runai.agents.scrub import scrub_text, scrub_url

API = "https://agp.eu.hcompany.ai/api/v2"
START = "https://race.example.org/"
HANDOFF = "https://race.example.org/registration"
PUBLIC_SHARE = "https://agp.eu.hcompany.ai/share/api/v1/trajectories/public-test"
IMAGE = b"synthetic screenshot bytes, not live evidence"
TASK = {
    "kind": "registration", "site_name": "Example race", "start_url": START,
    "instructions": "Read the public registration page and stop before any form.",
    "stop_before": ["form submission", "consent", "payment"],
    "success_signal": "Public registration page found", "fallback_url": START,
    "expected": {"edition": "2027", "race_date": "2027-04-04", "distance_km": 42.195},
}
ANSWER = {
    "status": "ready_for_payment", "handoff_url": HANDOFF,
    "reached_step": "Registration information found; stopped before any form.", "blocker": None,
    "verification": {
        **TASK["expected"], "selected": True, "next_safe_boundary": "participant data",
        "participant_data_untouched": True,
    },
}


@pytest.fixture(autouse=True)
def reviewed_policy(monkeypatch):
    def evaluate(url, kind):
        return {"allowed": True, "policy_id": "test-reviewed", "screenshot_scope": True,
                "expires_at": "2099-01-01T00:00:00Z",
                "allowed_hosts": [httpx.URL(url).host], "allowed_paths": ["/"]}
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy",
                        SimpleNamespace(evaluate_url=evaluate))


def observation(image=None):
    return {
        "type": "AgentEvent", "timestamp": "2026-11-08T20:00:00Z",
        "data": {
            "kind": "observation_event", "type": "web",
            "metadata": {"url": HANDOFF + "?session=private", "title": "Race entry"},
            "image": image or {
                "type": "base64", "media_type": "image/png",
                "source": base64.b64encode(IMAGE).decode(),
            },
        },
    }


class Provider:
    def __init__(self, *, answer=None, events=None, status="completed"):
        self.answer = ANSWER if answer is None else answer
        self.events = [observation()] if events is None else events
        self.status = status
        self.requests = []
        self.polls = 0

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if request.method == "POST" and path == "/api/v2/sessions":
            return httpx.Response(201, json={"id": "test-session", "agent_view_url": "private"})
        if request.method == "POST" and path.endswith("/share"):
            return httpx.Response(200, json={
                "share_url": "/share/api/v1/trajectories/public-test",
            })
        if request.method == "DELETE":
            return httpx.Response(204)
        if path.endswith("/force_answer"):
            return httpx.Response(409)
        if path.endswith("/changes"):
            self.polls += 1
            return httpx.Response(200, json={
                "status": self.status, "answer": self.answer,
                "new_events": self.events if self.polls == 1 else [],
                "first_index": 0 if self.polls == 1 else len(self.events),
            })
        if path == "/api/v2/sessions/test-session":
            return httpx.Response(200, json={"latest_answer": self.answer})
        raise AssertionError(f"Unexpected mock request {request.method} {path}")

    @property
    def cancelled(self):
        return any(request.method == "DELETE" for request in self.requests)


def run(provider, task=None, **kwargs):
    emitted = []

    async def execute():
        async def no_sleep(seconds):
            pass

        kwargs.setdefault("sleep", no_sleep)
        async def emit(event):
            emitted.append(event)

        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            runner = HAgentRunner("test-api-key", base_url=API, client=client, poll_s=0, **kwargs)
            result = await runner.run(task or TASK, emit)
            assert not client.is_closed
            return result

    return asyncio.run(execute()), emitted


@pytest.mark.parametrize("fields", [[], ["full_name"], ["email"]])
def test_prefill_prompt_is_scoped_and_outputs_private(fields):
    profile = {"full_name": "Sentinel Runnerxyz", "city": "Sentinelvillexyz"}
    effective = "full_name" in fields
    provider = Provider(answer={**ANSWER, "personal_data_entered": effective,
                                "reached_step": profile["full_name"].upper()})
    task = {**TASK, "runner_profile": profile, "prefill_fields": fields,
            "prefill_scope": "participant form"}
    result, events = run(provider, task)
    request = next(r for r in provider.requests if r.url.path == "/api/v2/sessions"
                   and r.method == "POST")
    prompt = json.loads(request.content)["messages"][0]["message"]
    assert (profile["full_name"] in prompt) == effective
    assert profile["city"] not in prompt
    if effective:
        assert ("Runner profile (type only into the participant form fields; "
                "never submit a final form)") in prompt
        assert result["reason_code"] != "unsafe_claim"
        assert result["prefilled"] is True
        assert result["stop_label"] == "payment page reached"
    assert all(v.casefold() not in str([result, events]).casefold() for v in profile.values())


@pytest.mark.parametrize("allowed", [False, True])
@pytest.mark.parametrize("claim", ["payment_executed", "booking_executed", "form_submitted",
                                   "account_created", "terms_accepted"])
def test_prefill_never_allows_commitment(claim, allowed):
    assert _payment_claim({claim: True}, allowed)
    assert _payment_claim({"personal_data_entered": True}, allowed) is not allowed


@pytest.mark.parametrize("profile,fields", [({}, ["full_name"]),
                                          ({"full_name": "Test Runner"}, [])])
def test_personal_data_claim_requires_effective_prefill(profile, fields):
    result, _ = run(Provider(answer={**ANSWER, "personal_data_entered": True}),
                    {**TASK, "runner_profile": profile, "prefill_fields": fields})
    assert result["reason_code"] == "unsafe_claim"


def test_prefill_page_never_forces_answer():
    task = {**TASK, "runner_profile": {"full_name": "Test Runner"},
            "prefill_fields": ["full_name"], "checkpoint": {
                "url_patterns": ["registration"], "beyond_patterns": [],
                "prefill_patterns": ["registration"],
            }}
    class PrefillProvider(Provider):
        def __call__(self, request):
            if request.url.path.endswith("/changes"):
                self.status = "running" if self.polls == 0 else "completed"
            return super().__call__(request)

    provider = PrefillProvider()
    run(provider, task, timeout_s=0.02)
    assert not any(r.url.path.endswith("/force_answer") for r in provider.requests)


def test_real_milan_registration_fallback_is_handoff_only(monkeypatch):
    monkeypatch.delitem(sys.modules, "runai.agents.site_policy")
    from runai.agents.registration import build_task

    task = build_task({"race": {
        "name": "Wizz Air Milano Marathon", "race_date": "2027-04-04",
        "country": "IT", "city": "Milano", "distance_km": 42.195,
        "official_url": "https://www.milanomarathon.it/",
    }, "arrival_date": "2027-04-03", "departure_date": "2027-04-05",
        "travelers": 1, "nights": 2}, today=date(2026, 11, 9))
    assert task["allowed_hosts"] == ["in.njuko.com"]
    assert task["fallback_url"] == "https://www.milanomarathon.it/"
    reviews = _policy(task)
    assert _reviewed(task["start_url"], reviews)
    assert not _reviewed(task["fallback_url"], reviews)


@pytest.mark.parametrize("failure", ["denied", "expired", "unknown", "raises"])
def test_handoff_fallback_fails_closed(monkeypatch, failure):
    def evaluate(url, kind):
        if url == "https://fallback.example/":
            if failure == "raises":
                raise ValueError("unknown site")
            if failure == "unknown":
                return None
            return {"allowed": failure != "denied", "expires_at": "2000-01-01"}
        return {"allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
                "allowed_hosts": ["race.example.org"]}

    monkeypatch.setitem(sys.modules, "runai.agents.site_policy",
                        SimpleNamespace(evaluate_url=evaluate))
    with pytest.raises(_PolicyBlocked):
        _policy({**TASK, "fallback_url": "https://fallback.example/"})


def blank_observation(url="about:blank"):
    event = observation()
    event["data"]["metadata"] = {} if url is None else {"url": url}
    return event


def frameless_observation(url=HANDOFF):
    event = blank_observation(url)
    event["data"].pop("image", None)
    return event


def test_vueling_blank_startup_then_reviewed_completion():
    fixture = json.loads((Path(__file__).parent / "fixtures/h_vueling_observations.json").read_text())
    events = fixture["changes"][0]["new_events"]
    url = events[1]["data"]["metadata"]["url"]
    expected = {"origin_city": "Paris", "city": "Barcelona", "arrival_date": "2027-04-03",
                "departure_date": "2027-04-05", "travelers": 1}
    provider = Provider(events=events, answer={
        **ANSWER, "handoff_url": url, "verification": {
            **expected, "selected": True, "next_safe_boundary": "passenger data",
            "fare": "Basic", "total": "120 EUR", "outbound_selected": True,
            "return_selected": True,
        },
    })

    def handle(request):
        response = provider(request)
        if request.url.path.endswith("/changes"):
            change = fixture["changes"][min(provider.polls - 1, 1)]
            return httpx.Response(200, json={**change, "answer": provider.answer})
        return response

    result, emitted = run(handle, task={**TASK, "kind": "transport", "expected": expected,
                                       "start_url": url, "fallback_url": url})
    assert result["status"] == "ready_for_payment"
    assert result["final_url"] == url
    assert len([e for e in emitted if e["type"] == "live_frame"]) == 1
    assert len([e for e in emitted if e.get("message") == "Navigation sur le site"]) == 1


@pytest.mark.parametrize("url", ["about:blank", "", None])
def test_blank_observations_after_reviewed_page_are_ignored(url):
    provider = Provider(events=[observation(), *[blank_observation(url) for _ in range(4)]])
    result, emitted = run(provider)
    assert result["status"] == "ready_for_payment"
    assert result["final_url"] == HANDOFF
    assert len([e for e in emitted if e["type"] == "live_frame"]) == 1
    assert len([e for e in emitted if e.get("message") == "Navigation sur le site"]) == 1


@pytest.mark.parametrize("deadline", [False, True])
def test_blank_startup_count_or_deadline_blocks(monkeypatch, deadline):
    now = 0
    provider = Provider(events=[blank_observation()] * (1 if deadline else 3), status="running")

    def handle(request):
        nonlocal now
        if deadline and request.url.path.endswith("/changes"):
            now = 45
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, emitted = run(handle, timeout_s=65 if deadline else 20)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "provider_error"
    assert result["summary"] == "Le site n'a pas pu s'ouvrir"
    assert result["final_url"] is None
    assert not any(e["type"] == "live_frame" for e in emitted)
    assert provider.cancelled


def test_blank_then_unreviewed_redirect_blocks():
    provider = Provider(events=[blank_observation(), blank_observation("https://evil.example/")])
    result, _ = run(provider)
    assert result["reason_code"] == "unreviewed_redirect"
    assert provider.cancelled


def test_blank_is_not_progress_for_retry():
    provider = Provider(events=[blank_observation()], status="failed")
    result, _ = run(provider)
    assert result["reason_code"] == "session_failed"
    assert sum(r.method == "POST" for r in provider.requests) == 2


def test_run_emits_real_api_frames_without_any_public_share():
    provider = Provider(events=[
        {"type": "LiveViewUrlEvent", "data": {"live_view_url": "https://private.example.org/"}},
        {"type": "AgentEvent", "data": {
            "kind": "policy_event", "content": "Opening public registration instructions",
            "reasoning_content": "PRIVATE reasoning is not emitted",
        }},
        observation(),
    ])
    result, events = run(provider)
    assert result["status"] == "ready_for_payment"
    assert result["handoff_url"] == HANDOFF
    assert result["start_url"] == START
    assert result["final_url"] == HANDOFF
    assert result["live_view_url"] is None
    assert not any(r.url.path.endswith("/share") for r in provider.requests)
    assert result["error"] is None
    frame = next(event for event in events if event["type"] == "live_frame")
    assert frame["image"] == IMAGE
    assert frame["mime"] == "image/png"
    assert frame["observed_at"] == "2026-11-08T20:00:00Z"
    assert not provider.cancelled
    assert "PRIVATE" not in repr(events) and "private.example" not in repr(events)
    assert provider.polls == 2
    assert provider.requests[-1].url.params["from_index"] == "3"
    body = json.loads(provider.requests[0].content)
    assert body["max_steps"] == 80 and body["max_time_s"] == 510
    assert body["overrides"]["agent.instructions"] == GUARDRAILS
    assert body["overrides"]["agent.environments[kind=web].start_url"] == START
    assert "stop_before" in body["messages"][0]["message"]
    assert "form submission" in body["messages"][0]["message"]


def test_missing_key_raises_without_network(monkeypatch):
    monkeypatch.delenv("HAI_API_KEY", raising=False)
    with pytest.raises(HUnavailable, match="HAI_API_KEY"):
        asyncio.run(HAgentRunner().run(TASK))


def test_key_can_come_from_environment(monkeypatch):
    monkeypatch.setenv("HAI_API_KEY", "test-only-env-key")
    assert HAgentRunner().api_key == "test-only-env-key"


@pytest.mark.parametrize("stage", ["create", "poll"])
def test_http_500_fails_without_provider_body_or_private_urls(stage):
    provider = Provider()

    def fail(request):
        if (stage == "create" and request.url.path == "/api/v2/sessions") or (
            stage == "poll" and request.url.path.endswith("/changes")
        ):
            return httpx.Response(500, text="Do not leak provider's private response")
        return provider(request)

    result, _ = run(fail)
    assert result["status"] == "failed" and result["error"] == "H HTTP 500"
    assert result["handoff_url"] is None
    assert provider.cancelled is (stage == "poll")
    assert "private response" not in repr(result)


@pytest.mark.parametrize("http_timeout", [False, True])
def test_timeout_calls_documented_delete(http_timeout):
    provider = Provider()

    async def slow(request):
        if request.url.path.endswith("/changes"):
            if http_timeout:
                raise httpx.ReadTimeout("private request details", request=request)
            await asyncio.Event().wait()
        return provider(request)

    result, _ = run(slow, timeout_s=0.02)
    assert result["status"] == "failed" and "timed out" in result["error"]
    assert provider.cancelled
    assert next(r for r in provider.requests if r.method == "DELETE").url.path == (
        "/api/v2/sessions/test-session"
    )


def test_cancellation_stops_remote_session_and_propagates():
    async def execute():
        provider = Provider()
        polling = asyncio.Event()

        async def slow(request):
            if request.url.path.endswith("/changes"):
                polling.set()
                await asyncio.Event().wait()
            return provider(request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
            work = asyncio.create_task(HAgentRunner("test-key", client=client).run(TASK))
            await asyncio.wait_for(polling.wait(), 1)
            work.cancel()
            with pytest.raises(asyncio.CancelledError):
                await work
        assert provider.cancelled

    asyncio.run(execute())


@pytest.mark.parametrize("url", [None, "", "http://race.example.org/entry", "javascript:alert(1)",
                                 "https://localhost/", "https://127.0.0.1/", "not-a-url"])
def test_no_safe_https_handoff_downgrades_to_blocked(url):
    result, _ = run(Provider(answer={**ANSWER, "handoff_url": url}))
    assert result["status"] == "blocked"
    assert result["handoff_url"] is None


@pytest.mark.parametrize("claim", [
    "Payment executed", "The booking was confirmed", "I paid the entry fee",
    "We have booked a room", "Purchase completed", "Paiement effectué",
    "Payment has been successfully processed", "I completed the purchase",
    "No form submitted, but I paid", "No account created; booking completed",
    "No payment executed, but I booked the room",
])
def test_payment_claim_fails_and_cancels(claim):
    provider = Provider(answer={**ANSWER, "reached_step": claim})
    result, _ = run(provider)
    assert result["status"] == "failed"
    assert "Safety violation" in result["error"]
    assert result["handoff_url"] is None and provider.cancelled


def test_unsafe_progress_cancels_before_emitting_claim():
    provider = Provider(events=[{"type": "AgentEvent", "data": {
        "kind": "policy_event", "content": "I booked the hotel",
    }}])
    result, events = run(provider)
    assert result["status"] == "failed" and provider.cancelled
    assert "I booked" not in repr(events)


@pytest.mark.parametrize("text", [
    "No payment executed. Not booked.", "I never booked the hotel", "I have not yet paid the fee",
])
def test_negative_payment_claim_is_not_an_execution_claim(text):
    result, _ = run(Provider(answer={**ANSWER, "reached_step": text}))
    assert result["status"] == "ready_for_payment"


def test_provider_blocker_never_becomes_success():
    result, _ = run(Provider(answer={**ANSWER, "blocker": "Captcha: human intervention required"}))
    assert result["status"] == "blocked" and "human assistance" in result["error"]


def test_provider_terminal_failure_is_not_success():
    result, _ = run(Provider(status="failed"))
    assert result["status"] == "blocked" and result["error"] == "H session failed"


def test_scrub_url_removes_credentials_fragments_and_sensitive_queries():
    url = (
        "https://user:password@race.example.org/entry;jsessionid=secret?"
        "distance=42&token=secret&session_id=secret&sid=secret&auth=secret&api_key=secret&"
        "X-Amz-Signature=secret&EMAIL=somebody%40example.org&jsessionid=secret#private"
    )
    assert scrub_url(url) == "https://race.example.org/entry?distance=42"
    assert scrub_url("https://race.example.org:bad/") is None
    assert scrub_url("https://agp.eu.hcompany.ai/api/v2/sessions/private") is None
    assert scrub_url("https://platform.hcompany.ai/share/other") is None
    assert scrub_url("https://agp.eu.hcompany.ai/share/other") is None
    assert scrub_url(PUBLIC_SHARE) is None


@pytest.mark.parametrize("path", [
    "/session/synthetic-private-token", "/entry/auth/synthetic-token", "/token=synthetic-value",
    "/entry/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", "/entry/runner%40example.org",
    "/entry/a1b2c3d4e5f6-synthetic-a7b8c9d0e1f2", "/entry/+33-6-12-34-56-78",
    "/entry/race-2027-123456789012345678901234567890",
    "/entry/runner-+33-6-12-34-56-78", "/entry/runner-%2B33-6-12-34-56-78",
    "/entry/road-sk-12345678",
    "/entry/sk-1234567", "/entry/road-hai-short",
    "/entry/runner-2028-04-02-25-30",
])
def test_private_session_and_contact_paths_are_not_returned_as_public_urls(path):
    url = "https://race.example.org" + path
    assert scrub_url(url) is None
    assert path not in scrub_text("Observed " + url)
    result, _ = run(Provider(answer={**ANSWER, "handoff_url": url}))
    assert result["status"] == "blocked" and result["handoff_url"] is None


def test_trip_dates_survive_url_scrubbing():
    url = "https://hotel.example.org/stay?checkin=2027-04-04&checkout=2027-04-06&token=private"
    assert scrub_url(url) == "https://hotel.example.org/stay?checkin=2027-04-04&checkout=2027-04-06"


@pytest.mark.parametrize("url,unsafe", [
    ("https://secure.booking.com/book.html?checkin=2027-04-04&checkout=2027-04-06", False),
    ("https://secure.booking.com/book.html?checkout=2027-04-06&checkin=2027-04-04", False),
    ("https://x.com/checkout", True),
    ("https://x.com/checkout/payment", True),
    ("https://x.com/checkout=review", True),
    ("https://x.com/review?next=checkout", True),
    ("https://x.com/review", False),
])
def test_checkout_date_query_is_not_an_unsafe_handoff(url, unsafe):
    expected = {"city": "Den Haag", "arrival_date": "2027-04-04",
                "departure_date": "2027-04-06", "travelers": 1}
    task = {"kind": "hotel", "expected": expected}
    answer = {"verification": {**expected, "room": "Standard", "rate": "Flexible",
                               "total": "240 EUR", "selected": True,
                               "next_safe_boundary": "guest details"}}
    reviews = [({"secure.booking.com", "x.com"}, ("/",))]
    failures = _verification_failures(task, answer, url, url, url, reviews)
    assert failures == (["unsafe_handoff"] if unsafe else [])


@pytest.mark.parametrize("separator", ["?", "&", ";"])
def test_checkout_exception_is_only_for_a_query_key(separator):
    from runai.agents.hclient import _FORBIDDEN

    assert not _FORBIDDEN.search(f"https://x.com/review{separator}checkout=2027-04-06")
    assert _FORBIDDEN.search(f"https://x.com/review{separator}checkout")
    assert _FORBIDDEN.search(f"https://x.com/review{separator}checkout/payment")


@pytest.mark.parametrize("url", [
    "https://in.njuko.com/wizz-air-milano-marathon-20271776152378557",
    "https://inscripciones.rpmsports.es/es/evento/zurich-marato-barcelona-2027/my-registration",
    "https://race.example.org/northern-city-road-marathon-2028-04-02",
    "https://race.example.org/event/1234567890",
    "https://race.example.org/northern-city-road-marathon-2028-04-02-10-30",
])
def test_public_word_slugs_work_as_start_handoff_and_progress_urls(url):
    assert scrub_url(url) == url
    message = "Read " + url + " then stop"
    assert scrub_text(message) == message
    expected = {**TASK["expected"], "race_date": "2028-04-02"} if "2028" in url else TASK["expected"]
    provider = Provider(
        answer={**ANSWER, "handoff_url": url,
                "verification": {**ANSWER["verification"], **expected}},
        events=[{**observation(), "data": {**observation()["data"], "metadata": {"url": url}}},
                {"type": "AgentEvent", "data": {"kind": "policy_event", "content": message}}],
    )
    result, events = run(provider, task={**TASK, "start_url": url, "expected": expected})
    assert result["status"] == "ready_for_payment"
    assert result["start_url"] == result["handoff_url"] == url
    assert not any(e.get("message") == message for e in events)
    body = json.loads(provider.requests[0].content)
    assert body["overrides"]["agent.environments[kind=web].start_url"] == url


def test_scrub_text_preserves_dates_and_removes_contacts_keys_and_private_urls():
    value = scrub_text(
        "Race 2027-04-04. Contact runner@example.org or +33 6 12 34 56 78. "
        "sk-test-only-not-a-real-credential Bearer synthetic-credential "
        "https://user:pass@race.example.org/?token=private&distance=42#fragment "
        "https://agp.eu.hcompany.ai/api/v2/sessions/private"
    )
    assert "2027-04-04" in value
    for secret in ("runner@", "+33", "sk-test", "synthetic-credential", "user:pass", "token=", "/sessions/"):
        assert secret not in value
    assert "distance=42" in value


def test_all_emitted_messages_and_returned_urls_are_scrubbed():
    frame = observation()
    frame["data"]["metadata"]["url"] = HANDOFF + "?token=secret&distance=42"
    provider = Provider(
        answer={**ANSWER, "handoff_url": HANDOFF + "?token=secret&distance=42#private",
                "reached_step": "runner@example.org +33 6 12 34 56 78 test-api-key"},
        events=[{"type": "AgentEvent", "data": {
            "kind": "policy_event", "content": "runner@example.org test-api-key",
        }}, frame],
    )
    result, events = run(provider)
    assert "runner@" not in repr((result, events))
    assert "test-api-key" not in repr((result, events))
    assert "token=" not in repr((result, events))
    assert result["handoff_url"] == HANDOFF + "?distance=42"


def test_step_cap_cancels_remote_run_and_clamps_requested_limit():
    provider = Provider(status="running")

    def capped(request):
        if request.url.path.endswith("/changes"):
            return httpx.Response(200, json={
                "status": "running", "new_events": [], "metrics": {"steps": 120},
            })
        return provider(request)

    result, _ = run(capped, task={**TASK, "max_steps": 500})
    assert result["status"] == "failed" and "step limit" in result["error"]
    assert json.loads(provider.requests[0].content)["max_steps"] == 80
    assert provider.cancelled


def test_inline_image_url_download_does_not_leak_authorization():
    provider = Provider(events=[observation({
        "type": "url", "source": "https://images.example.org/shot.png?signature=synthetic",
        "media_type": "image/png",
    })])

    def image_request(request):
        if request.url.host == "images.example.org":
            assert not request.headers.get("Authorization")
            return httpx.Response(200, content=IMAGE, headers={"content-type": "image/png"})
        return provider(request)

    result, events = run(image_request)
    assert result["status"] == "ready_for_payment"
    assert next(e for e in events if e["type"] == "live_frame")["image"] == IMAGE


@pytest.mark.parametrize("target", [
    "https://127.0.0.1/private", "https://169.254.169.254/private",
    "http://images.example.org/insecure", "https://localhost/private",
])
def test_screenshot_redirects_cannot_reach_private_or_insecure_targets(target):
    provider = Provider(events=[observation({
        "type": "url", "source": "https://images.example.org/frame.png", "media_type": "image/png",
    })])

    def image_request(request):
        if request.url.host == "images.example.org":
            return httpx.Response(302, headers={"location": target})
        assert request.url.host == "agp.eu.hcompany.ai"
        return provider(request)

    result, events = run(image_request)
    assert result["status"] == "failed" and provider.cancelled
    assert not any(e["type"] == "live_frame" for e in events)


@pytest.mark.parametrize("source", [
    API + "/sessions/test-session/resources/screenshots/frame.png",
    "https://agp.eu.hcompany.ai/api/v1/trajectories/test-session/resources/screenshots/frame.png",
    "/api/v1/trajectories/test-session/resources/screenshots/frame.png?version=latest",
])
def test_authenticated_screenshot_resource_redirect_drops_bearer(source):
    provider = Provider(events=[observation({
        "type": "url", "source": source, "media_type": "image/png",
    })])

    def image_request(request):
        if request.url.path.endswith("/resources/screenshots/frame.png"):
            assert request.url.path == "/api/v2/sessions/test-session/resources/screenshots/frame.png"
            assert request.url.query == httpx.URL(source).query
            assert request.headers["Authorization"] == "Bearer test-api-key"
            return httpx.Response(302, headers={"location": "https://images.example.org/frame.png"})
        if request.url.host == "images.example.org":
            assert not request.headers.get("Authorization")
            return httpx.Response(200, content=IMAGE, headers={"content-type": "image/png"})
        return provider(request)

    result, events = run(image_request)
    assert result["status"] == "ready_for_payment"
    assert next(e for e in events if e["type"] == "live_frame")["image"] == IMAGE


@pytest.mark.parametrize("source", [
    "https://agp.eu.hcompany.ai/api/v1/trajectories/other-session/resources/screenshots/frame.png",
    "https://images.example.org/api/v1/trajectories/test-session/resources/screenshots/frame.png",
])
def test_legacy_foreign_or_cross_session_resource_is_not_authenticated_or_rewritten(source):
    provider = Provider(events=[observation({
        "type": "url", "source": source, "media_type": "image/png",
    })])
    resource_requests = []

    def handle(request):
        if "/resources/" in request.url.path:
            resource_requests.append(request)
            assert str(request.url) == source
            assert not request.headers.get("Authorization")
            return httpx.Response(404)
        return provider(request)

    result, events = run(handle)
    assert len(resource_requests) == 1
    # A refused screenshot never kills the run, but without a frame no stop is verified.
    assert result["status"] == "blocked" and not any(e["type"] == "live_frame" for e in events)
    assert not any(event["type"] == "live_frame" for event in events)


def test_empty_polls_and_deferred_answer_are_drained():
    provider = Provider()
    polls = 0

    def deferred(request):
        nonlocal polls
        if request.url.path.endswith("/changes"):
            polls += 1
            if polls == 1:
                return httpx.Response(204)
            return httpx.Response(200, json={"status": "completed", "new_events": []})
        return provider(request)

    result, _ = run(deferred)
    assert result["status"] == "blocked" and polls == 2
    assert any(r.url.path == "/api/v2/sessions/test-session" for r in provider.requests)


def test_terminal_poll_followed_by_204_finishes_instead_of_timing_out():
    provider = Provider()
    polls = 0

    def terminal_then_empty(request):
        nonlocal polls
        if request.url.path.endswith("/changes"):
            polls += 1
            if polls > 1:
                return httpx.Response(204)
        return provider(request)

    result, events = run(terminal_then_empty, timeout_s=1)
    assert result["status"] == "ready_for_payment" and not provider.cancelled
    assert any(e["type"] == "live_frame" for e in events)


def test_progress_never_uses_action_names_or_echoes_user_prompt_or_tool_arguments():
    provider = Provider(events=[
        {"type": "AgentEvent", "data": {
            "kind": "message_event", "caller_id": "user", "content": ["do not echo this task"],
        }},
        {"type": "AgentEvent", "data": {
            "kind": "policy_event", "content": None,
            "tool_reqs": [{"tool_name": "scroll_web", "args": {"private": "not for logs"}}],
        }},
    ])
    result, events = run(provider)
    assert result["status"] == "blocked"
    assert "scroll_web" not in repr(events)
    assert "do not echo" not in repr(events) and "not for logs" not in repr(events)


def test_consumer_failure_cancels_remote_run():
    async def execute():
        provider = Provider()

        async def broken(_event):
            raise RuntimeError("sensitive consumer exception must not leak")

        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            result = await HAgentRunner("test-key", client=client).run(TASK, broken)
        assert provider.cancelled
        assert result["status"] == "failed" and "sensitive" not in result["error"]

    asyncio.run(execute())


@pytest.mark.parametrize("failure", ["invalid_response", "consumer"])
def test_cancel_failure_is_reported_for_parse_and_consumer_errors(failure):
    async def execute():
        provider = Provider()

        def handle(request):
            if request.method == "DELETE":
                return httpx.Response(500)
            if failure == "invalid_response" and request.url.path.endswith("/changes"):
                return httpx.Response(200, content=b"not JSON")
            return provider(request)

        async def consume(_event):
            if failure == "consumer":
                raise RuntimeError("private callback details")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await HAgentRunner("test-key", client=client).run(TASK, consume)
        assert result["status"] == "failed" and "cancellation failed" in result["error"]
        assert "private callback" not in result["error"]

    asyncio.run(execute())


def test_scrub_short_assigned_credentials():
    value = scrub_text('api_key="synthetic-value" access_token=synthetic-token secret: synthetic')
    assert "synthetic" not in value


def test_url_valued_credentials_are_not_preserved_as_public_links():
    value = scrub_text(
        'api_key="https://private.example.org/assigned" '
        'Bearer https://private.example.org/bearer'
    )
    assert "private.example.org" not in value


@pytest.mark.parametrize("task", [
    {**TASK, "start_url": "https://race.example.org/test-api-key"},
    {**TASK, "start_url": "https://127.0.0.1/"},
    {**TASK, "max_steps": 0}, {**TASK, "max_steps": True},
])
def test_invalid_task_does_not_start_remote_run_or_leak_key(task):
    provider = Provider()
    result, _ = run(provider, task=task)
    assert result["status"] == "failed"
    assert not provider.requests
    assert "test-api-key" not in repr(result)


def test_parallel_runs_use_independent_remote_sessions():
    async def execute():
        sessions = {}

        def handle(request):
            if request.method == "POST" and request.url.path == "/api/v2/sessions":
                sid = f"session-{len(sessions)}"
                sessions[sid] = 0
                return httpx.Response(201, json={"id": sid})
            sid = request.url.path.split("/")[4]
            if request.url.path.endswith("/share"):
                return httpx.Response(200, json={
                    "share_url": f"/share/api/v1/trajectories/{sid}",
                })
            if request.url.path.endswith("/changes"):
                sessions[sid] += 1
                return httpx.Response(200, json={
                    "status": "completed", "answer": {**ANSWER, "handoff_url": HANDOFF + "/" + sid},
                    "new_events": [{**observation(), "data": {
                        **observation()["data"], "metadata": {"url": HANDOFF + "/" + sid},
                    }}] if sessions[sid] == 1 else [],
                })
            raise AssertionError("Unexpected concurrent mock request")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            runner = HAgentRunner("test-key", client=client)
            results = await asyncio.gather(runner.run(TASK), runner.run(TASK), runner.run(TASK))
        assert len({r["handoff_url"] for r in results}) == 3
        assert all(r["status"] == "ready_for_payment" for r in results)
        assert len(sessions) == 3

    asyncio.run(execute())


@pytest.mark.parametrize("change", [
    {"allowed": False}, {"expires_at": "2000-01-01"},
    {"screenshot_scope": False}, {"allowed_hosts": []}, {"policy_id": None},
])
def test_policy_denials_never_create_provider_session(monkeypatch, change):
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(
        evaluate_url=lambda *_: {
            "allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
            "allowed_hosts": ["race.example.org"], "expires_at": "2099-01-01", **change,
        },
    ))
    provider = Provider()
    result, _ = run(provider)
    assert result["status"] == "blocked" and not provider.requests


def test_missing_policy_fails_closed(monkeypatch):
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", None)
    provider = Provider()
    result, _ = run(provider)
    assert result["status"] == "blocked" and not provider.requests


@pytest.mark.parametrize("task", [
    {**TASK, "start_url": "http://all.accor.com/"},
    {**TASK, "allowed_hosts": []},
    {**TASK, "allowed_hosts": ["other.example.org"]},
    {**TASK, "fallback_url": "http://all.accor.com/"},
])
def test_planned_hosts_and_fallback_checked_before_create(task):
    provider = Provider()
    result, _ = run(provider, task)
    assert result["status"] in {"blocked", "failed"} and not provider.requests


def test_accor_no_longer_has_hclient_specific_exclusion():
    assert _policy({**TASK, "start_url": "https://all.accor.com/",
                    "fallback_url": "https://all.accor.com/"})


@pytest.mark.parametrize("budget,expected", [(1, 1), (80, 80), (100, 80), (120, 80), (500, 80)])
def test_bounded_budget_support(budget, expected):
    provider = Provider()
    result, _ = run(provider, {**TASK, "max_steps": budget})
    assert result["status"] == "ready_for_payment"
    assert json.loads(provider.requests[0].content)["max_steps"] == expected


@pytest.mark.parametrize("field,value", [
    ("edition", "2026"), ("race_date", "2027-04-05"), ("distance_km", 21.1),
    ("selected", False), ("participant_data_untouched", False), ("next_safe_boundary", ""),
])
def test_forged_verification_is_not_ready(field, value):
    result, _ = run(Provider(answer={**ANSWER, "verification": {
        **ANSWER["verification"], field: value,
    }}))
    assert result["status"] == "blocked"


@pytest.mark.parametrize("answer", [
    {**ANSWER, "verification": {}}, {**ANSWER, "verification": None},
    {**ANSWER, "handoff_url": START}, {**ANSWER, "handoff_url": HANDOFF + "?date=2026-04-04"},
    {**ANSWER, "handoff_url": "https://race.example.org/search"},
    {**ANSWER, "handoff_url": "https://race.example.org/login"},
    {**ANSWER, "handoff_url": "https://agp.eu.hcompany.ai/share/api/v1/trajectories/public"},
])
def test_unverified_or_unselected_handoffs_blocked(answer):
    result, _ = run(Provider(answer=answer))
    assert result["status"] == "blocked"


@pytest.mark.parametrize("metadata", [
    {"url": "https://unreviewed.example.org/entry"},
    {"url": "https://race.example.org/login"},
    {"url": HANDOFF, "title": "runner@example.org"},
    {"url": HANDOFF, "title": "Payment card details"},
])
def test_unsafe_observed_context_suppresses_frame_and_cancels(metadata):
    event = observation()
    event["data"]["metadata"] = metadata
    provider = Provider(events=[event])
    result, events = run(provider)
    assert result["status"] == "blocked" and provider.cancelled
    assert not any(e["type"] == "live_frame" for e in events)
    assert "runner@" not in repr((result, events))


def test_terminal_final_frame_drained_through_204():
    provider = Provider()
    polls = 0

    def handle(request):
        nonlocal polls
        if request.url.path.endswith("/changes"):
            polls += 1
            if polls == 1:
                return httpx.Response(200, json={
                    "status": "completed", "answer": ANSWER, "first_index": 0,
                    "new_events": [{"type": "AgentEvent", "data": {"kind": "policy_event"}}],
                })
            if polls == 2:
                return httpx.Response(200, json={
                    "status": "completed", "first_index": 1, "new_events": [observation()],
                })
            return httpx.Response(204)
        return provider(request)

    result, events = run(handle)
    assert result["status"] == "ready_for_payment" and polls == 3
    assert sum(e["type"] == "live_frame" for e in events) == 1
    assert not any(r.url.path.endswith("/share") for r in provider.requests)


@pytest.mark.parametrize("kind", ["hotel", "transport"])
@pytest.mark.parametrize("mismatch", [None, "arrival_date", "departure_date", "travelers"])
def test_kind_specific_selection_and_expected_party(kind, mismatch):
    expected = {"kind": kind, "city": "Rome", "origin_city": "Paris",
                "arrival_date": "2027-04-03", "departure_date": "2027-04-05", "travelers": 2}
    verification = {**expected, "selected": True, "next_safe_boundary": "guest details",
                    "room": "Twin", "rate": "Flexible", "total": "EUR 1200",
                    "fare": "Return flexible", "outbound_selected": True, "return_selected": True}
    if mismatch:
        verification[mismatch] = 3 if mismatch == "travelers" else "2027-04-06"
    result, _ = run(Provider(answer={**ANSWER, "verification": verification}),
                    {**TASK, "kind": kind, "expected": expected})
    assert result["status"] == ("blocked" if mismatch else "ready_for_payment")


@pytest.mark.parametrize("mime,size", [("text/html", 20), ("image/png", 5 * 1024 * 1024 + 1)])
def test_invalid_resource_mime_or_size_cancels(mime, size):
    provider = Provider(events=[observation({
        "type": "url", "source": "https://images.example.org/frame", "media_type": "image/png",
    })])

    def handle(request):
        if request.url.host == "images.example.org":
            return httpx.Response(200, content=b"x" * size, headers={"content-type": mime})
        return provider(request)

    result, events = run(handle)
    assert result["status"] == "failed" and provider.cancelled
    assert not any(e["type"] == "live_frame" for e in events)


@pytest.mark.parametrize("text", ["Login required", "Account wall", "Registration closed"])
def test_self_reported_wall_cannot_be_ready(text):
    result, _ = run(Provider(answer={**ANSWER, "reached_step": text}))
    assert result["status"] == "blocked"
    assert text not in result["summary"]


@pytest.mark.parametrize("claim", ["I accepted terms", "I created an account", "Form submitted"])
def test_forbidden_action_claim_cancels(claim):
    provider = Provider(answer={**ANSWER, "reached_step": claim})
    result, _ = run(provider)
    assert result["status"] == "failed" and provider.cancelled


def test_sentinel_payloads_never_appear_in_results_events_or_logs(caplog):
    sentinel = "runner@example.org 4111-1111-1111-1111 password=sentinel test-api-key"
    provider = Provider(events=[
        {"type": "AgentEvent", "data": {"kind": "policy_event", "content": sentinel}},
        observation(),
    ], answer={**ANSWER, "reached_step": sentinel})
    result, events = run(provider)
    rendered = repr((result, events)) + caplog.text
    for value in ("runner@", "4111-1111", "password=sentinel", "test-api-key"):
        assert value not in rendered
    assert result["status"] == "ready_for_payment"


def test_missing_expected_blocks_even_with_structured_answer():
    result, _ = run(Provider(), {**TASK, "expected": {}})
    assert result["status"] == "blocked"


def test_partial_outcome_blocks_even_with_verification():
    provider = Provider()

    def handle(request):
        response = provider(request)
        if request.url.path.endswith("/changes"):
            return httpx.Response(200, json={**response.json(), "outcome": "partial"})
        return response

    result, _ = run(handle)
    assert result["status"] == "blocked"


def test_other_session_resource_never_receives_bearer():
    provider = Provider(events=[observation({
        "type": "url", "source": API + "/sessions/other/resources/screenshots/frame.png",
        "media_type": "image/png",
    })])

    def handle(request):
        if "/sessions/other/" in request.url.path:
            assert not request.headers.get("Authorization")
            return httpx.Response(403)
        return provider(request)

    result, events = run(handle)
    # A refused screenshot never kills the run, but without a frame no stop is verified.
    assert result["status"] == "blocked" and not any(e["type"] == "live_frame" for e in events)


def test_navigation_login_text_is_not_a_forbidden_page():
    event = observation()
    event["data"]["metadata"]["text"] = "Log in | Account | Payment checkout | Race information"
    provider = Provider(events=[event])
    result, events = run(provider)
    assert result["status"] == "ready_for_payment" and not provider.cancelled
    assert any(event["type"] == "live_frame" for event in events)


def test_checkout_observation_handoff_remains_blocked_and_terminal_session_stops():
    event = observation()
    event["data"]["metadata"] = {"url": HANDOFF + "/checkout", "title": "Checkout"}
    provider = Provider(events=[event], answer={**ANSWER, "handoff_url": HANDOFF + "/checkout"})
    result, events = run(provider)
    assert result["status"] == "blocked" and provider.cancelled
    assert any(event["type"] == "live_frame" for event in events)


def test_policy_no_expiry_and_reviewed_hosts_without_synthetic_root_calls(monkeypatch):
    calls = []

    def evaluate(url, kind):
        calls.append((url, kind))
        assert url == START
        return {"allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
                "expires_at": None, "allowed_hosts": ["race.example.org", "entry.example.org"]}

    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(evaluate_url=evaluate))
    provider = Provider()
    result, _ = run(provider, {**TASK, "allowed_hosts": ["race.example.org", "entry.example.org"]})
    assert result["status"] == "ready_for_payment"
    assert calls == [(START, "registration"), (START, "registration")]


def test_extra_planned_host_outside_review_blocks_without_create(monkeypatch):
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(
        evaluate_url=lambda *_: {
            "allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
            "expires_at": None, "allowed_hosts": ["race.example.org"],
        },
    ))
    provider = Provider()
    result, _ = run(provider, {**TASK, "allowed_hosts": ["race.example.org", "outside.example.org"]})
    assert result["status"] == "blocked" and not provider.requests


@pytest.mark.parametrize("distance", [42.2, "42.195 km", "42,2"])
def test_registration_only_compares_relevant_normalized_expected(distance):
    expected = {**TASK["expected"], "kind": "registration", "race_name": "Marathon de Milan",
                "arrival_date": "2027-04-03", "departure_date": "2027-04-05", "travelers": 2,
                "city": "Milan", "country": "Italy"}
    provider = Provider(answer={**ANSWER, "verification": {
        **ANSWER["verification"], "race_date": "2027-04-04T12:00:00Z", "distance_km": distance,
        "race_name": "MARATHON DE MILANÓ",
    }})
    result, _ = run(provider, {**TASK, "expected": expected})
    assert result["status"] == "ready_for_payment"
    properties = json.loads(provider.requests[0].content)["overrides"]["agent.answer_format"][
        "properties"]["verification"]["properties"]
    assert not {"arrival_date", "departure_date", "travelers", "city", "country", "kind"} & (
        properties.keys()
    )


@pytest.mark.parametrize("kind", ["hotel", "transport"])
def test_trip_verification_normalizes_city_party_and_dates_without_race_fields(kind):
    expected = {"kind": kind, "city": "Milan", "origin_city": "Paris", "country": "Italy",
                "arrival_date": "2027-04-03T00:00:00Z", "departure_date": "2027-04-05",
                "travelers": 2, "race_date": "2027-04-04", "race_name": "Other race"}
    verification = {"city": "Milano", "origin_city": "PARÍS", "arrival_date": "2027-04-03",
                    "departure_date": "2027-04-05T18:00:00Z", "travelers": "2",
                    "selected": True, "next_safe_boundary": "guest details", "room": "Twin",
                    "rate": "Flexible", "fare": "Flexible", "total": "EUR 1200",
                    "outbound_selected": True, "return_selected": True}
    provider = Provider(answer={**ANSWER, "verification": verification})
    result, _ = run(provider, {**TASK, "kind": kind, "expected": expected})
    assert result["status"] == "ready_for_payment"
    properties = json.loads(provider.requests[0].content)["overrides"]["agent.answer_format"][
        "properties"]["verification"]["properties"]
    assert not {"race_date", "race_name", "country", "kind"} & properties.keys()


@pytest.mark.parametrize("format_kind", ["aware", "naive", "date"])
def test_policy_expiry_uses_timestamp_precision_and_date_inclusive_day(monkeypatch, format_kind):
    earlier = datetime.now(UTC) - timedelta(seconds=1)
    expiry = earlier.isoformat()
    if format_kind == "naive":
        expiry = earlier.replace(tzinfo=None).isoformat()
    elif format_kind == "date":
        expiry = datetime.now(UTC).date().isoformat()
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(
        evaluate_url=lambda *_: {
            "allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
            "expires_at": expiry, "allowed_hosts": ["race.example.org"],
        },
    ))
    provider = Provider()
    result, _ = run(provider)
    if format_kind == "date":
        assert result["status"] == "ready_for_payment"
    else:
        assert result["status"] == "blocked" and not provider.requests


@pytest.mark.parametrize("prefix,path,allowed", [
    ("/race", "/race", True), ("/race", "/race/entry", True),
    ("/race/", "/race/entry", True), ("/race", "/race-private", False),
    ("/", "/race-private", True), ("/race/", "/race", False),
    ("/", "", True), ("", "", True), ("/race", "", False),
])
def test_reviewed_paths_respect_segment_boundaries(prefix, path, allowed):
    assert _reviewed("https://race.example.org" + path,
                     [({"race.example.org"}, (prefix,))]) is allowed


def test_start_path_outside_reviewed_segment_never_creates_session(monkeypatch):
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(
        evaluate_url=lambda *_: {
            "allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
            "expires_at": None, "allowed_hosts": ["race.example.org"], "allowed_paths": ["/race"],
        },
    ))
    provider = Provider()
    result, _ = run(provider, {**TASK, "start_url": "https://race.example.org/race-private"})
    assert result["status"] == "blocked" and not provider.requests


def test_homepage_without_trailing_slash_is_in_reviewed_root_scope(monkeypatch):
    monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(
        evaluate_url=lambda *_: {
            "allowed": True, "policy_id": "reviewed", "screenshot_scope": True,
            "expires_at": None, "allowed_hosts": ["race.example.org"], "allowed_paths": ["/"],
        },
    ))
    provider = Provider()
    result, _ = run(provider, {**TASK, "start_url": START.rstrip("/"),
                             "fallback_url": START.rstrip("/")})
    assert result["status"] == "ready_for_payment"
    assert any(r.method == "POST" and r.url.path == "/api/v2/sessions" for r in provider.requests)


@pytest.mark.parametrize("query", ["room=twin", "fare=flexible"])
def test_handoff_query_must_match_observed_selection(query):
    provider = Provider(answer={**ANSWER, "handoff_url": HANDOFF + "?" + query})
    result, _ = run(provider)
    assert result["status"] == "blocked"


@pytest.mark.parametrize("kind,day,ready", [
    ("transport", "2027-04-02", True), ("transport", "2027-04-01", False),
    ("hotel", "2027-04-02", False),
])
def test_transport_overnight_outbound_date_allowance(kind, day, ready):
    expected = {"city": "Rome", "origin_city": "Paris", "arrival_date": "2027-04-03",
                "departure_date": "2027-04-05", "travelers": 2}
    verification = {**expected, "selected": True, "next_safe_boundary": "guest details",
                    "room": "Twin", "rate": "Flexible", "fare": "Return", "total": "EUR 1200",
                    "outbound_selected": True, "return_selected": True}
    url = HANDOFF + "?outbound=" + day
    event = observation()
    event["data"]["metadata"]["url"] = url
    result, _ = run(Provider(events=[event], answer={
        **ANSWER, "handoff_url": url, "verification": verification,
    }), {**TASK, "kind": kind, "expected": expected})
    assert result["status"] == ("ready_for_payment" if ready else "blocked")


@pytest.mark.parametrize("query,ready", [
    ("outbound=2027-04-02&return=2027-04-05", True),
    ("outbound=2027-04-03&return=2027-04-02", False),
    ("outbound=2027-04-03&inbound=2027-04-04", False),
    ("outbound=2027-04-03&return=2027-04-05&returnUrl=/trips", True),
    ("outbound=2027-04-03&return=2027-04-02&returnUrl=/trips", False),
])
def test_transport_return_date_must_match_departure(query, ready):
    expected = {"city": "Rome", "origin_city": "Paris", "arrival_date": "2027-04-03",
                "departure_date": "2027-04-05", "travelers": 2}
    verification = {**expected, "selected": True, "next_safe_boundary": "passenger details",
                    "fare": "Return", "total": "EUR 300",
                    "outbound_selected": True, "return_selected": True}
    url = HANDOFF + "?" + query
    event = observation()
    event["data"]["metadata"]["url"] = url
    result, _ = run(Provider(events=[event], answer={
        **ANSWER, "handoff_url": url, "verification": verification,
    }), {**TASK, "kind": "transport", "expected": expected})
    assert result["status"] == ("ready_for_payment" if ready else "blocked")


@pytest.mark.parametrize("timeout,provider_budget", [(600, 510), (120, 30), (90, 45), (10, 5)])
def test_provider_time_budget_leaves_local_final_answer_headroom(timeout, provider_budget):
    provider = Provider()
    result, _ = run(provider, timeout_s=timeout)
    assert result["status"] == "ready_for_payment"
    assert json.loads(provider.requests[0].content)["max_time_s"] == pytest.approx(
        provider_budget, abs=0.01,
    )


@pytest.mark.parametrize("text", [
    "No payment or booking was executed", "Stopped before booking",
    "Stopped before any booking is confirmed", "Payment not yet completed",
    "payment is completed only after clicking Pay",
    "Next safe boundary: booking is confirmed only after the payment step",
    "stop before the booking is confirmed or payment is completed",
    "No account created and booking completed",
    "https://www.endu.net/en/events/x/book",
    "https://example.org/booking/confirmed", "payment_executed: false",
    {"payment_executed": False}, {"stop_before": "Booking confirmed"},
    None, "", [], {"reached_step": "sans paiement effectué"},
])
def test_r3_safe_claims(text):
    assert not _payment_claim(text)


@pytest.mark.parametrize("text", [
    "I have paid", "I paid the deposit", "Booking confirmed",
    "The payment was successfully completed", "We booked the room",
    "Your reservation is confirmed", "J'ai payé", "réservation confirmée",
    "paiement effectué", "No booking executed, however I paid",
    "I paid the deposit and no refund is possible",
    "I paid after clicking Pay", "Booking confirmed after the payment step",
    "Pas de paiement mais réservation confirmée",
    *[{key: True} for key in ("payment_executed", "booking_executed", "form_submitted",
                             "account_created", "terms_accepted", "personal_data_entered")],
])
def test_r3_affirmative_claims(text):
    assert _payment_claim(text)


@pytest.mark.parametrize("blocker,reason", [
    ("Captcha required", "captcha"), ("Connexion requise", "login_required"),
    ("Account required", "login_required"), ("Consenso necessario", "consent_required"),
    ("Sold out", "sold_out"), ("Épuisé", "sold_out"), ("Ausverkauft", "sold_out"),
    ("Registration closed", "registration_closed"),
    ("Closed for the requested dates", "registration_closed"),
    ("Verification not completed", "unsafe_claim"),
    ("Inscripciones cerradas", "registration_closed"),
    ("No results for these dates", "no_inventory"), ("No trains", "no_inventory"),
    ("Aucun résultat", "no_inventory"), ("Nessun risultato", "no_inventory"),
    ("Sem resultados", "no_inventory"), ("Keine Zimmer verfügbar", "no_inventory"),
    ("Over budget", "over_budget"), ("Wrong date", "date_mismatch"),
    ("", "unsafe_claim"),
])
def test_r3_completed_blocked_reasons(blocker, reason):
    result, _ = run(Provider(answer={**ANSWER, "status": "blocked", "blocker": blocker}))
    assert result["status"] == "blocked"
    assert result["reason_code"] == reason


def test_r3_verification_date_reason():
    result, _ = run(Provider(answer={**ANSWER, "verification": {
        **ANSWER["verification"], "race_date": "2027-04-05",
    }}))
    assert result["reason_code"] == "date_mismatch"


@pytest.mark.parametrize("path,reason", [
    ("login", "login_required"), ("captcha", "captcha"),
    ("outside", "unreviewed_redirect"), ("payment-card", "policy_denied"),
])
def test_r3_observed_policy_reasons(path, reason):
    event = observation()
    event["data"]["metadata"] = {"url": (
        "https://outside.example.org/" if path == "outside" else START + path
    )}
    provider = Provider(events=[event])
    result, _ = run(provider)
    assert result["reason_code"] == reason and provider.cancelled


@pytest.mark.parametrize("status", ["failed", "interrupted"])
@pytest.mark.parametrize("recover", [True, False])
def test_r3_retry_once_before_observation(status, recover):
    provider = Provider(events=[], status=status)
    creates = 0

    def handle(request):
        nonlocal creates
        if request.method == "POST":
            creates += 1
            return httpx.Response(201, json={"id": f"session-{creates}"})
        if recover and creates == 2 and request.url.path.endswith("/changes"):
            provider.polls += 1
            return httpx.Response(200, json={
                "status": "completed", "answer": ANSWER,
                "new_events": [observation()] if provider.polls == 2 else [],
            })
        return provider(request)

    result, _ = run(handle)
    assert creates == 2
    assert provider.cancelled
    assert result["reason_code"] == (None if recover else "session_failed")


def test_r3_no_retry_after_observation():
    provider = Provider(status="failed")
    result, _ = run(provider)
    assert result["reason_code"] == "session_failed"
    assert sum(r.method == "POST" for r in provider.requests) == 1


def test_fake_clock_new_observation_cadence_retry_and_no_refetch(monkeypatch):
    now = 0.0
    attempts = []
    polls = 0
    provider = Provider()
    image = {"type": "url", "source": "https://images.example.org/latest",
             "media_type": "image/png"}

    def handle(request):
        nonlocal now, polls
        if request.url.path.endswith("/changes"):
            polls += 1
            now += int(request.url.params["wait_for_seconds"])
            new_events = [observation(image)] if polls in {1, 3} else []
            if polls == 3:
                new_events[0]["data"]["image"] = {**image, "source": "https://images.example.org/new"}
            return httpx.Response(200, json={
                "status": "running" if polls < 5 else "completed", "answer": ANSWER,
                "new_events": new_events,
            })
        if request.url.host == "images.example.org":
            attempts.append((request.url.path, now))
            if len(attempts) == 1:
                return httpx.Response(503)
            return httpx.Response(200, content=IMAGE + request.url.path.encode(),
                                  headers={"content-type": "image/png"})
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            events = []

            async def emit(event):
                events.append({**event, "emitted_at": now})

            result = await HAgentRunner("key", client=client, base_url=API, poll_s=30).run(TASK, emit)
            return result, events

    result, events = asyncio.run(execute())
    assert result["reason_code"] is None
    assert attempts == [("/latest", 2), ("/latest", 4), ("/new", 6)]
    frames = [e for e in events if e["type"] == "live_frame"]
    assert len(frames) == 2
    assert frames[0]["emitted_at"] - 2 <= 3
    assert frames[1]["emitted_at"] - 6 <= 3


@pytest.mark.parametrize("status", ["timed_out", "failed"])
def test_r3_timeout_status_and_error_code(status):
    provider = Provider(events=[], status=status)

    def handle(request):
        response = provider(request)
        if request.url.path.endswith("/changes"):
            return httpx.Response(200, json={**response.json(), "error_code": "timeout"})
        return response

    result, _ = run(handle)
    assert result["reason_code"] == "timeout"


def test_r3_runtime_defaults():
    assert HAgentRunner("key").timeout_s == 900
    assert HAgentRunner("key", timeout_s=1200).timeout_s == 900


def test_stale_frame_from_previous_page_never_verifies_new_handoff():
    first = observation()
    first["data"]["metadata"] = {"url": HANDOFF + "/step1", "title": "Race entry"}
    second = observation()
    del second["data"]["image"]
    result, _ = run(Provider(events=[first, second]))
    assert result["status"] == "blocked"


def test_next_safe_boundary_description_is_not_an_execution_claim():
    from runai.agents.hclient import _payment_claim
    assert not _payment_claim({"verification": {
        "selected": True, "next_safe_boundary": "booking is confirmed after payment",
    }})
    assert _payment_claim({"verification": {"next_safe_boundary": "x"}, "summary": "I paid"})
    for claim in ("I paid", "We have booked the room", "J'ai payé", "Stop before payment. I paid",
                  "Avant le paiement, j'ai réservé"):
        assert _payment_claim({"verification": {"next_safe_boundary": claim}})
    for safe in ("Stop before I have booked the room", "Avant que j'ai payé", "before we paid"):
        assert not _payment_claim({"verification": {"next_safe_boundary": safe}})


def alternative_provider(providers):
    current = -1

    def handle(request):
        nonlocal current
        if request.method == "POST" and request.url.path.endswith("/sessions"):
            current += 1
        return providers[current](request)

    return handle


def test_alternative_after_redirect_returns_ready():
    first = Provider(events=[blank_observation("https://evil.example/")])
    second = Provider()
    result, emitted = run(alternative_provider([first, second]),
                          task={**TASK, "alternatives": [dict(TASK)]})
    assert result["status"] == "ready_for_payment"
    assert first.cancelled
    assert second.polls == 2
    assert any(e.get("message") == "Essai d’un autre site" for e in emitted)


def test_alternative_policy_failure_skipped_without_session(monkeypatch):
    evaluate = sys.modules["runai.agents.site_policy"].evaluate_url

    def policy(url, kind):
        return {"allowed": False} if "denied.example" in url else evaluate(url, kind)

    monkeypatch.setitem(sys.modules, "runai.agents.site_policy",
                        SimpleNamespace(evaluate_url=policy))
    first, second = Provider(status="failed", events=[frameless_observation()]), Provider()
    result, _ = run(alternative_provider([first, second]), task={
        **TASK, "alternatives": [{**TASK, "start_url": "https://denied.example/"}, dict(TASK)],
    })
    assert result["status"] == "ready_for_payment"
    assert sum(r.method == "POST" for p in (first, second) for r in p.requests) == 2


def test_alternatives_all_blocked_return_last_without_upgrade():
    first = Provider(status="failed", events=[frameless_observation()])
    second = Provider(answer={**ANSWER, "status": "blocked", "blocker": "Sold out"})
    result, _ = run(alternative_provider([first, second]),
                    task={**TASK, "alternatives": [dict(TASK)]})
    assert result["status"] == "blocked"
    assert result["reason_code"] == "sold_out"
    assert result["handoff_url"] == TASK["fallback_url"]
    assert first.cancelled and second.cancelled


def test_blocked_alternative_uses_its_own_policy_checked_fallback():
    first = Provider(events=[blank_observation("https://evil.example/")])
    second = Provider(answer={**ANSWER, "status": "blocked", "blocker": "Sold out"})
    fallback = "https://alternative.example/registration"
    result, _ = run(alternative_provider([first, second]), task={
        **TASK, "alternatives": [{**TASK, "fallback_url": fallback}],
    })
    assert result["status"] == "blocked"
    assert result["reason_code"] == "sold_out"
    assert result["handoff_url"] == fallback
    assert result["handoff_url"] != TASK["fallback_url"]


@pytest.mark.parametrize("kind,expected", [
    ("registration", {"race_date": "2027-04-04", "distance_km": 42.195}),
    ("hotel", {"arrival_date": "2027-04-03", "departure_date": "2027-04-05", "travelers": 1}),
    ("transport", {"origin_city": "Paris", "city": "Milan", "arrival_date": "2027-04-03",
                   "departure_date": "2027-04-05", "travelers": 1}),
])
@pytest.mark.parametrize("invalid", ["missing", "empty", "partial", "null", "blank"])
def test_unverifiable_alternatives_are_skipped_without_replacing_primary(kind, expected, invalid):
    alternative = {**TASK, "kind": kind, "expected": expected}
    if invalid == "missing":
        alternative.pop("expected")
    elif invalid == "empty":
        alternative["expected"] = {}
    else:
        alternative["expected"] = dict(expected)
        for key in expected:
            broken = dict(alternative["expected"])
            if invalid == "partial":
                broken.pop(key)
            else:
                broken[key] = None if invalid == "null" else ""
            provider = Provider(events=[blank_observation("https://evil.example/")])
            result, emitted = run(provider, task={
                **TASK, "kind": kind, "alternatives": [{**alternative, "expected": broken}],
            })
            assert result["reason_code"] == "unreviewed_redirect"
            assert sum(r.method == "POST" for r in provider.requests) == 1
            assert not any(e.get("message") == "Essai d'un autre site" for e in emitted)
        return
    provider = Provider(events=[blank_observation("https://evil.example/")])
    result, _ = run(provider, task={**TASK, "kind": kind, "alternatives": [alternative]})
    assert result["reason_code"] == "unreviewed_redirect"
    assert sum(r.method == "POST" for r in provider.requests) == 1


@pytest.mark.parametrize("alternatives", [None, {}, "invalid", [], [None, {},
    {**TASK, "kind": "hotel"}], [{**TASK, "max_steps": False}]])
def test_missing_or_invalid_alternatives_ignored(alternatives):
    provider = Provider(status="failed")
    result, _ = run(provider, task={**TASK, "alternatives": alternatives})
    assert result["reason_code"] == "session_failed"
    assert sum(r.method == "POST" for r in provider.requests) == 1


@pytest.mark.parametrize("reason", ["unsafe_claim", "login_required", "policy_denied"])
def test_nonlisted_reason_never_tries_alternative(reason, monkeypatch):
    provider = Provider(events=[blank_observation("https://evil.example/")])
    if reason == "unsafe_claim":
        provider = Provider(answer={**ANSWER, "reached_step": "I paid"})
    elif reason == "login_required":
        provider = Provider(events=[blank_observation(HANDOFF + "/login")])
    else:
        monkeypatch.setitem(sys.modules, "runai.agents.site_policy", SimpleNamespace(
            evaluate_url=lambda *args: {"allowed": False},
        ))
    result, emitted = run(provider, task={**TASK, "alternatives": [dict(TASK)]})
    assert result["reason_code"] == reason
    assert sum(r.method == "POST" for r in provider.requests) <= 1
    assert not any(e.get("message") == "Essai d'un autre site" for e in emitted)


@pytest.mark.parametrize("status", ["failed", "interrupted"])
def test_session_failed_after_progress_offers_reviewed_handoff(status):
    provider = Provider(status=status)
    result, _ = run(provider)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "session_failed"
    assert result["handoff_url"] == HANDOFF
    assert result["summary"] == "Le site s'est interrompu ; reprenez depuis le dernier écran"
    assert provider.cancelled


def test_alternatives_share_overall_deadline(monkeypatch):
    now = 0
    provider = Provider(status="failed")

    def handle(request):
        nonlocal now
        if request.url.path.endswith("/changes") and provider.polls:
            now = 600
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, _ = run(handle, task={**TASK, "alternatives": [dict(TASK)]})
    assert result["reason_code"] == "session_failed"
    assert sum(r.method == "POST" for r in provider.requests) == 1


def test_all_sequential_alternatives_are_used_until_ready():
    providers = [Provider(status="failed", events=[frameless_observation()])
                 for _ in range(3)] + [Provider()]
    result, _ = run(alternative_provider(providers),
                    task={**TASK, "alternatives": [dict(TASK)] * 3})
    assert result["status"] == "ready_for_payment"
    assert all(sum(r.method == "POST" for r in p.requests) == 1 for p in providers)


def test_newest_observation_supersedes_older_pending_frames():
    provider = Provider()
    fetched = []

    def image_event(name):
        return observation({"type": "url", "source": f"https://images.example.org/{name}",
                            "media_type": "image/png"})

    def handle(request):
        if request.url.host == "images.example.org":
            fetched.append(request.url.path)
            if request.url.path == "/old":
                return httpx.Response(503)
            return httpx.Response(200, content=request.url.path.encode(),
                                  headers={"content-type": "image/png"})
        response = provider(request)
        if request.url.path.endswith("/changes"):
            batches = [[image_event("old")], [image_event("middle"), image_event("newest")],
                       [image_event("last")], []]
            return httpx.Response(200, json={
                "status": "running" if provider.polls < 4 else "completed",
                "answer": ANSWER, "new_events": batches[provider.polls - 1],
            })
        return response

    result, events = run(handle)
    assert result["status"] == "ready_for_payment"
    assert fetched == ["/old", "/newest", "/last"]
    assert [event["image"] for event in events if event["type"] == "live_frame"] == [
        b"/newest", b"/last",
    ]


CHECKPOINT = {"url_patterns": [r"^/registration(?:\?|$)"],
              "beyond_patterns": [r"/pay(?:/|\?|$)", r"/passengers"]}


def test_synthetic_checkpoint_fixture_matches_casefolded_unquoted_path_query():
    fixture = json.loads((Path(__file__).parent / "fixtures/h_checkpoint_observations.json").read_text())
    assert fixture["synthetic"] is True
    checkpoint = _checkpoint({"checkpoint": fixture["checkpoint"]})
    for row in fixture["observations"]:
        assert _checkpoint_matches(checkpoint, "url_patterns", row["url"]) == row["stop"]
        assert _checkpoint_matches(checkpoint, "beyond_patterns", row["url"]) == row["beyond"]


class CheckpointProvider(Provider):
    def __init__(self, batches, **kwargs):
        super().__init__(**kwargs)
        self.batches = iter(batches)

    def __call__(self, request):
        if request.url.path.endswith("/force_answer"):
            self.requests.append(request)
            return httpx.Response(202)
        if request.url.path.endswith("/changes"):
            self.requests.append(request)
            return httpx.Response(200, json=next(self.batches))
        return super().__call__(request)


def batch(*events, state="running", **kwargs):
    return {"status": state, "new_events": list(events), **kwargs}


@pytest.mark.parametrize("create_state", ["queued", {"status": "pending"}])
def test_queued_120_seconds_then_running_does_not_use_startup_budget(monkeypatch, create_state):
    now = 0
    provider = Provider()

    def handle(request):
        nonlocal now
        response = provider(request)
        if request.method == "POST":
            return httpx.Response(201, json={"id": "test-session", "status": create_state})
        if request.url.path.endswith("/changes"):
            now = [120, 121, 122][provider.polls - 1]
            if provider.polls == 1:
                return httpx.Response(200, json=batch(*[blank_observation()] * 4, state="queued"))
            return httpx.Response(200, json=batch(
                *([observation()] if provider.polls == 2 else []),
                state="completed" if provider.polls == 3 else "running", answer=ANSWER,
            ))
        return response

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, emitted = run(handle)
    assert result["status"] == "ready_for_payment"
    assert sum(e.get("message") == "En attente d'un navigateur disponible" for e in emitted) == 1
    assert provider.requests[0].headers["Idempotency-Key"]


@pytest.mark.parametrize("end_state", ["queued", "running"])
def test_queue_wait_over_eight_minutes_is_blocked(monkeypatch, end_state):
    now = 0
    provider = Provider()

    def handle(request):
        nonlocal now
        response = provider(request)
        if request.method == "POST":
            return httpx.Response(201, json={"id": "test-session", "status": "queued"})
        if request.url.path.endswith("/changes"):
            now = 481
            return httpx.Response(200, json=batch(state=end_state))
        return response

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, _ = run(handle)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "provider_error"
    assert provider.cancelled


def test_alternatives_share_eight_minute_total_queue_limit(monkeypatch):
    now, creates = 0, 0
    provider = Provider()

    def handle(request):
        nonlocal now, creates
        response = provider(request)
        if request.method == "POST" and request.url.path.endswith("/sessions"):
            creates += 1
            return httpx.Response(201, json={"id": "test-session", "status": "queued"})
        if request.url.path.endswith("/changes"):
            if creates == 1:
                now = 300
                return httpx.Response(200, json=batch(blank_observation("https://evil.example/")))
            now = 481
            return httpx.Response(200, json=batch(state="queued"))
        return response

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, _ = run(handle, {**TASK, "alternatives": [dict(TASK), dict(TASK)]})
    assert result["status"] == "blocked"
    assert result["reason_code"] == "provider_error"
    assert creates == 2 and provider.cancelled


def test_checkpoint_frame_precedes_exactly_one_force_and_verified_answer():
    provider = CheckpointProvider([
        batch(observation()), batch(observation(), metrics={"steps": 78}),
        batch(state="completed", answer=ANSWER),
    ])
    result, events = run(provider, {**TASK, "checkpoint": CHECKPOINT})
    assert result["status"] == "ready_for_payment"
    assert result["handoff_url"] == HANDOFF
    assert sum(r.url.path.endswith("/force_answer") for r in provider.requests) == 1
    assert any(e["type"] == "live_frame" for e in events)
    prompt = json.loads(provider.requests[0].content)["messages"][0]["message"]
    assert "Stop page hints" in prompt
    assert not any("url_patterns" in e.get("message", "") for e in events)


def test_completed_checkpoint_consumes_existing_answer_without_restarting_browser():
    provider = CheckpointProvider([
        batch(observation(), state="completed", answer=ANSWER),
        batch(state="completed", answer=ANSWER),
    ])
    result, events = run(provider, {**TASK, "checkpoint": CHECKPOINT})
    assert result["status"] == "ready_for_payment"
    assert result["handoff_url"] == HANDOFF
    assert any(e["type"] == "live_frame" for e in events)
    assert not any(r.url.path.endswith("/force_answer") for r in provider.requests)


def test_step_limit_tightens_prior_checkpoint_answer_wait_to_45_seconds(monkeypatch):
    now, polls = 0, 0
    provider = CheckpointProvider([
        batch(observation()), batch(metrics={"steps": 77}), batch(metrics={"steps": 78}),
    ])

    def handle(request):
        nonlocal now, polls
        if request.url.path.endswith("/changes"):
            now = [0, 10, 46][polls]
            polls += 1
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, _ = run(handle, {**TASK, "checkpoint": CHECKPOINT})
    assert result["reason_code"] == "step_limit"
    assert sum(r.url.path.endswith("/force_answer") for r in provider.requests) == 1
    assert provider.cancelled and now == 46


@pytest.mark.parametrize("verification,ready", [
    (json.dumps(ANSWER["verification"]), True),
    ("not JSON", False), ("[]", False), ("null", False), ([], False), (42, False),
])
def test_provider_stringified_verification_is_decoded_or_fails_closed(verification, ready):
    provider = CheckpointProvider([
        batch(observation()),
        batch(state="completed", answer={**ANSWER, "verification": verification}),
    ])
    result, _ = run(provider, {**TASK, "checkpoint": CHECKPOINT})
    assert result["status"] == ("ready_for_payment" if ready else "blocked")
    assert result["error"] is None if ready else result["error"] == "Verification unavailable or site blocked"


@pytest.mark.parametrize("claim", [False, True])
@pytest.mark.parametrize("prior_checkpoint", [False, True])
def test_beyond_checkpoint_cancels_and_never_ready(claim, prior_checkpoint):
    beyond = blank_observation("https://race.example.org/pay/payments?token=secret")
    batches = [batch(observation())] if prior_checkpoint else []
    batches += [batch(beyond, answer={**ANSWER, "booking_executed": True} if claim else ANSWER)]
    provider = CheckpointProvider(batches)
    result, _ = run(provider, {**TASK, "checkpoint": CHECKPOINT})
    assert result["status"] == "blocked"
    assert result["reason_code"] == ("unsafe_claim" if claim else "policy_denied")
    assert result["handoff_url"] == (HANDOFF if prior_checkpoint else None)
    assert provider.cancelled


@pytest.mark.parametrize("checkpoint", [None, {}, [], {"url_patterns": ["("], "beyond_patterns": []},
    {"url_patterns": [True], "beyond_patterns": []},
    {"url_patterns": [""], "beyond_patterns": []},
    {"url_patterns": [r"/other"], "beyond_patterns": []}])
def test_invalid_or_unmatched_present_checkpoint_fails_closed(checkpoint):
    result, _ = run(Provider(), {**TASK, "checkpoint": checkpoint})
    assert result["status"] == "blocked"


@pytest.mark.parametrize("from_error", [False, True])
def test_step_budget_forces_answer_before_step_limit(from_error):
    provider = CheckpointProvider([
        batch(observation(), metrics={"steps": 77}, **(
            {"error_code": "step_limit", "status": "failed"} if from_error else {}
        )), batch(state="completed", answer=ANSWER),
    ])
    result, _ = run(provider)
    assert result["status"] == "ready_for_payment"
    assert sum(r.url.path.endswith("/force_answer") for r in provider.requests) == 1


def test_force_answer_wait_is_bounded(monkeypatch):
    now = 0
    provider = CheckpointProvider([batch(observation(), metrics={"steps": 77}), batch()])

    def handle(request):
        nonlocal now
        if request.url.path.endswith("/changes") and any(
            r.url.path.endswith("/force_answer") for r in provider.requests
        ):
            now = 46
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, _ = run(handle)
    assert result["reason_code"] == "step_limit"
    assert provider.cancelled


@pytest.mark.parametrize("kind", ["hotel", "transport"])
@pytest.mark.parametrize("city,ready", [("Amsterdam", True), ("Den Haag", True), ("Rotterdam", False)])
def test_gateway_city_is_an_additional_expected_city_only(kind, city, ready):
    expected = {"city": "Den Haag", "gateway_city": "Amsterdam", "origin_city": "Paris",
                "arrival_date": "2027-04-03", "departure_date": "2027-04-05", "travelers": 1}
    answer = {**ANSWER, "verification": {
        **expected, "city": city, "selected": True, "next_safe_boundary": "guest data",
        "room": "Standard", "rate": "Flex", "total": "120 EUR", "fare": "Basic",
        "outbound_selected": True, "return_selected": True,
    }}
    result, _ = run(Provider(answer=answer), {**TASK, "kind": kind, "expected": expected})
    assert result["status"] == ("ready_for_payment" if ready else "blocked")


@pytest.mark.parametrize("flag,fragment,kept", [
    (True, "/booking/train?from=Paris&to=Amsterdam", True),
    (False, "/booking/train?from=Paris", False),
    (True, "/booking/train?token=private", False),
    (True, "/booking/runner@example.org", False),
])
def test_keep_fragment_only_preserves_public_routes(flag, fragment, kept):
    provider = Provider()
    start = START + "#" + fragment
    run(provider, {**TASK, "start_url": start, "keep_fragment": flag})
    requested = json.loads(provider.requests[0].content)["overrides"][
        "agent.environments[kind=web].start_url"]
    assert requested == (start if kept else START)


def test_retry_create_uses_new_idempotency_key():
    provider = Provider(status="failed", events=[])
    run(provider)
    keys = [r.headers["Idempotency-Key"] for r in provider.requests
            if r.method == "POST" and r.url.path.endswith("/sessions")]
    assert len(keys) == 2 and len(set(keys)) == 2


def test_unreviewed_redirect_has_public_host_path_diagnostic_only():
    provider = Provider(events=[blank_observation("https://other.example.org/flights?email=a@b.fr#x")])
    result, emitted = run(provider)
    assert result["reason_code"] == "unreviewed_redirect"
    assert result["blocked_url_host"] == "other.example.org/flights"
    assert "other.example.org/flights" in repr(result["steps"])
    assert not any("other.example.org" in e.get("message", "") for e in emitted)
    assert "a@b.fr" not in repr(result)


def test_redirect_diagnostic_never_contains_current_api_key():
    result, _ = run(Provider(events=[blank_observation("https://evil.example/test-api-key")]))
    assert result["reason_code"] == "unreviewed_redirect"
    assert result["blocked_url_host"] is None
    assert "test-api-key" not in repr(result)


def test_checkpoint_final_answer_cannot_verify_a_different_final_page():
    other = HANDOFF + "/other"
    provider = CheckpointProvider([
        batch(observation()),
        batch(blank_observation(other), state="completed", answer={**ANSWER, "handoff_url": other}),
    ])
    result, _ = run(provider, {**TASK, "checkpoint": CHECKPOINT})
    assert result["status"] == "blocked"


def test_present_checkpoint_is_applied_to_alternative_not_primary():
    bad = Provider(events=[blank_observation("https://evil.example/")])
    good = CheckpointProvider([batch(observation()), batch(state="completed", answer=ANSWER)])
    result, _ = run(alternative_provider([bad, good]), task={
        **TASK, "alternatives": [{**TASK, "checkpoint": CHECKPOINT}],
    })
    assert result["status"] == "ready_for_payment"
    assert sum(r.url.path.endswith("/force_answer") for r in good.requests) == 1


@pytest.mark.parametrize("url", ["about:srcdoc", "chrome://newtab",
                                      "data:text/html,", "blob:https://race.example.org/id"])
def test_browser_internal_urls_are_blank_not_redirects(url):
    provider = Provider(events=[blank_observation(url), observation()])
    result, _ = run(provider)
    assert result["status"] == "ready_for_payment"
    assert not result.get("blocked_url_host")


def test_step_progress_is_monotonic_and_uses_only_provider_metrics():
    provider = CheckpointProvider([batch(observation(), metrics={"steps": n}) for n in [1, 1, 3, 2]] + [
        batch(state="completed", answer=ANSWER),
    ])
    result, events = run(provider)
    assert result["status"] == "ready_for_payment"
    assert [e["message"] for e in events if e.get("message", "").startswith("Étape")] == [
        "Étape 1", "Étape 3",
    ]


def ihg_case():
    fixture = json.loads((Path(__file__).parent / "fixtures/h_ihg_observations.json").read_text())
    task = {**TASK, "kind": "hotel", "start_url": fixture["urls"][0],
            "fallback_url": fixture["urls"][0], "expected": fixture["expected"],
            "checkpoint": fixture["checkpoint"]}
    events = []
    for url in fixture["urls"]:
        event = observation()
        event["data"]["metadata"] = {"url": url, "title": "Hotel selection"}
        events.append(event)
    return fixture, task, events


@pytest.mark.parametrize("field,value,gate", [
    ("room", None, "missing_room"), ("rate", None, "missing_rate"),
    ("total", None, "missing_total"), ("selected", False, "selected"),
    ("next_safe_boundary", None, "next_safe_boundary"),
    ("city", "Rotterdam", "expected_city"), ("travelers", 3, "expected_travelers"),
])
def test_ihg_unverified_checkpoint_is_honest_public_handoff(field, value, gate):
    fixture, task, events = ihg_case()
    answer = fixture["answer"]
    answer["verification"][field] = value
    result, emitted = run(Provider(events=events, answer=answer), task)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "checkpoint_unverified"
    assert result["checkpoint_reached"] is True
    assert result["handoff_url"] == scrub_url(fixture["urls"][-1])
    diagnostic = next(step for step in result["steps"] if step.startswith("verify_failed:"))
    assert gate in json.loads(diagnostic.split(": ", 1)[1])
    assert all(word not in diagnostic for word in ["Rotterdam", "Milan", "240 EUR", "2027"])
    assert not any("verify_failed" in repr(event) for event in emitted)


@pytest.mark.parametrize("succeed_on", [1, 2, 3, None])
@pytest.mark.parametrize("verification", ["empty", "missing_total"])
def test_ihg_unverified_checkpoint_retains_frame_downloaded_on_retry(succeed_on, verification):
    fixture, task, observations = ihg_case()
    answer = fixture["answer"]
    if verification == "empty":
        answer["verification"] = {}
    else:
        answer["verification"]["total"] = None
    checkpoint = observations[-1]
    checkpoint["data"]["image"] = {
        "type": "url", "source": "https://images.example.org/checkpoint",
        "media_type": "image/png",
    }
    provider = Provider(events=[checkpoint], answer=answer)
    attempts = 0

    def handle(request):
        nonlocal attempts
        if request.url.host == "images.example.org":
            attempts += 1
            if succeed_on is None or attempts < succeed_on:
                return httpx.Response(503)
            return httpx.Response(200, content=IMAGE, headers={"content-type": "image/png"})
        return provider(request)

    result, events = run(handle, task)
    frames = [event for event in events if event["type"] == "live_frame"]
    assert result["status"] == "blocked"
    if succeed_on is not None:
        assert attempts == succeed_on
        assert len(frames) == 1 and frames[0]["image"] == IMAGE
        assert result["reason_code"] == "checkpoint_unverified"
        assert result["checkpoint_reached"] is True
        assert result["handoff_url"] == scrub_url(fixture["urls"][-1])
    else:
        assert attempts == 3
        assert not frames and not result.get("checkpoint_reached")
        assert result["handoff_url"] is None
        assert result["reason_code"] == "unsafe_claim"


def test_ihg_complete_checkpoint_ready_with_zero_based_july_and_tracking_noise():
    fixture, task, events = ihg_case()
    result, _ = run(Provider(events=events, answer=fixture["answer"]), task)
    assert result["status"] == "ready_for_payment"
    assert result["handoff_url"] == scrub_url(fixture["urls"][-1])


def test_ihg_wrong_url_month_is_date_mismatch():
    fixture, task, events = ihg_case()
    for event in events:
        event["data"]["metadata"]["url"] = event["data"]["metadata"]["url"].replace("062027", "052027")
    fixture["answer"]["handoff_url"] = fixture["answer"]["handoff_url"].replace("062027", "052027")
    result, _ = run(Provider(events=events, answer=fixture["answer"]), task)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "date_mismatch"


@pytest.mark.parametrize("suffix", ["guest-details", "payment"])
def test_ihg_beyond_checkpoint_never_ready(suffix):
    fixture, task, events = ihg_case()
    events.append(blank_observation("https://www.ihg.com/reservation/" + suffix))
    result, _ = run(Provider(events=events, answer=fixture["answer"]), task)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "policy_denied"


def test_ihg_checkpoint_without_frame_cannot_establish_p13_or_ready():
    fixture, task, events = ihg_case()
    for event in events:
        event["data"].pop("image")
    result, _ = run(Provider(events=events, answer=fixture["answer"]), task)
    assert result["status"] == "blocked"
    assert not result.get("checkpoint_reached")
    assert "checkpoint_frame" in repr(result["steps"])


@pytest.mark.parametrize("verification", [None, {}, [], "invalid JSON"])
def test_ihg_empty_or_invalid_verification_is_checkpoint_unverified(verification):
    fixture, task, events = ihg_case()
    fixture["answer"]["verification"] = verification
    result, _ = run(Provider(events=events, answer=fixture["answer"]), task)
    assert result["status"] == "blocked"
    assert result["reason_code"] == "checkpoint_unverified"
    assert result["checkpoint_reached"] is True


def test_no_observations_heartbeat_is_spaced_monotonic_and_has_no_frames(monkeypatch):
    now = 0
    polls = iter([0, 21, 41, 61, 62])
    initial = blank_observation(HANDOFF)
    initial["data"].pop("image", None)
    provider = CheckpointProvider([
        batch(initial, metrics={"steps": 2}),
        batch(metrics={"steps": 2}), batch(metrics={"steps": 1}),
        batch(metrics={"steps": 4}), batch(state="completed", answer=ANSWER),
    ])
    emitted = []

    def handle(request):
        nonlocal now
        if request.url.path.endswith("/changes"):
            now = next(polls)
        return provider(request)

    async def execute():
        async def emit(event):
            emitted.append((now, event.copy()))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await HAgentRunner("test-api-key", base_url=API, client=client, poll_s=0).run(
                TASK, emit,
            )

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result = asyncio.run(execute())
    heartbeats = [(at, event["message"]) for at, event in emitted
                  if "l'agent lit la page" in event.get("message", "")]
    assert [at for at, _ in heartbeats] == [21, 41, 61]
    assert all(b[0] - a[0] >= 20 for a, b in pairwise(heartbeats))
    numbers = [int(event["message"].split()[1]) for _, event in emitted
               if event.get("message", "").startswith("Étape")]
    assert numbers == sorted(numbers)
    assert not any(event["type"] == "live_frame" for _, event in emitted)
    assert all(not any(word in message for word in ["http", "JSON", "prompt"])
               for _, message in heartbeats)
    durations = [json.loads(step.split(": ", 1)[1]) for step in result["steps"]
                 if step.startswith("h_step_duration:")]
    assert durations == [
        {"from_step": 0, "to_step": 2, "duration_s": 0},
        {"from_step": 2, "to_step": 4, "duration_s": 61},
    ]
    assert not any("h_step_duration" in repr(event) for _, event in emitted)


@pytest.mark.parametrize("url", ["chrome-error://chromewebdata/", "chrome://chromewebdata/",
                                      "about:neterror?e=connectionFailure", "about:certerror"])
def test_initial_browser_error_blocks_within_20_seconds(monkeypatch, url):
    fixture = json.loads((Path(__file__).parent / "fixtures/h_vueling_observations.json").read_text())
    changes = fixture["unreachable_changes"]
    changes[-1]["new_events"][0]["data"]["metadata"]["url"] = url
    provider = CheckpointProvider(changes)
    now = 0

    def handle(request):
        nonlocal now
        if request.url.path.endswith("/changes"):
            now += 5
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    result, events = run(handle, timeout_s=20)
    assert now <= 20
    assert result["status"] == "blocked"
    assert result["reason_code"] == "provider_error"
    assert "site_unreachable_in_h" in result["steps"]
    assert "site_unreachable_in_h" not in result["summary"]
    assert not any("site_unreachable_in_h" in repr(event) for event in events)
    assert not any(event["type"] == "live_frame" for event in events)
    assert provider.cancelled
    assert sum(request.url.path == "/api/v2/sessions" for request in provider.requests) == 1


def test_browser_error_after_reviewed_progress_is_not_initial_startup_failure():
    result, _ = run(Provider(events=[observation(), blank_observation("about:neterror")]))
    assert result["status"] == "ready_for_payment"
    assert "site_unreachable_in_h" not in result["steps"]


def runtime_result(reason="provider_error", status="blocked", error=None):
    return {"status": status, "reason_code": reason, "error": error,
            "steps": [], "summary": "Preparation unavailable", "handoff_url": None}


def runtime_attempts(monkeypatch, outcomes, *, alternatives=2, durations=None):
    now, calls, waits, events = [0.0], [], [], []
    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now[0])

    class RuntimeRunner(HAgentRunner):
        async def _attempt(self, task, on_event, timeout_s, queue_wait=None):
            index = len(calls)
            calls.append((task["site_name"], timeout_s))
            result, framed = outcomes[index]
            if framed:
                await on_event({"type": "live_frame", "image": IMAGE})
            if durations:
                now[0] += durations[index]
            return dict(result)

    async def execute():
        async def sleep(seconds):
            waits.append(seconds)
            now[0] += seconds

        async def emit(event):
            events.append(event)

        task = {**TASK, "alternatives": [{**TASK, "site_name": f"alternate-{i}"}
                                         for i in range(alternatives)]}
        return await RuntimeRunner("test-key", sleep=sleep).run(task, emit)

    return asyncio.run(execute()), calls, waits, events


@pytest.mark.parametrize("reason,status", [("provider_error", "failed"),
                                         ("provider_error", "blocked"),
                                         ("no_site_coverage", "blocked"),
                                         ("session_failed", "blocked")])
def test_runtime_unframed_failure_switches_once(monkeypatch, reason, status):
    ready = runtime_result(None, "ready_for_payment")
    result, calls, waits, events = runtime_attempts(
        monkeypatch, [(runtime_result(reason, status), False), (ready, True)],
    )
    assert result["status"] == "ready_for_payment"
    assert len(calls) == 2 and not waits
    assert [e["message"] for e in events if e["type"] == "step_progress"] == [
        "Essai d’un autre site",
    ]


@pytest.mark.parametrize("reason,framed", [
    ("captcha", False), ("consent_required", False), ("login_required", False),
    ("policy_denied", False), ("checkpoint_unverified", False), ("unsafe_claim", False),
    ("provider_error", True), ("session_failed", True), ("sold_out", True),
])
def test_runtime_safety_or_any_frame_prevents_switch(monkeypatch, reason, framed):
    result, calls, waits, events = runtime_attempts(
        monkeypatch, [(runtime_result(reason), framed)],
    )
    assert result["reason_code"] == reason
    assert len(calls) == 1 and not waits
    assert not any(e["type"] == "step_progress" for e in events)


def test_browser_startup_retries_same_task_once_then_alternative(monkeypatch):
    failed = runtime_result(error="Browser startup unavailable")
    ready = runtime_result(None, "ready_for_payment")
    result, calls, waits, events = runtime_attempts(
        monkeypatch, [(failed, False), (failed, False), (ready, True)],
    )
    assert result["status"] == "ready_for_payment"
    assert [item[0] for item in calls] == [TASK["site_name"], TASK["site_name"], "alternate-0"]
    assert waits == [20]
    assert sum(e.get("message") == "Essai d’un autre site" for e in events) == 1


def test_runtime_900_second_budget_includes_retry_delay(monkeypatch):
    failed = runtime_result(error="Browser startup unavailable")
    result, calls, waits, _ = runtime_attempts(
        monkeypatch, [(failed, False), (runtime_result(), False), (runtime_result(), False)],
        durations=[400, 300, 180],
    )
    assert result["status"] == "blocked"
    assert waits == [20]
    assert [item[1] for item in calls] == [600, 480, 180]


def test_runtime_ready_and_empty_alternatives_stop(monkeypatch):
    ready = runtime_result(None, "ready_for_payment")
    result, calls, waits, events = runtime_attempts(monkeypatch, [(ready, True)], alternatives=0)
    assert result["status"] == "ready_for_payment" and len(calls) == 1
    assert not waits and len(events) == 1


@pytest.mark.parametrize("blocker", ["provider_error", "no_site_coverage"])
def test_runtime_provider_answers_reach_alternative_loop(blocker):
    first = Provider(events=[frameless_observation()], answer={
        **ANSWER, "status": "blocked", "blocker": blocker,
    })
    second = Provider()
    result, events = run(alternative_provider([first, second]),
                         {**TASK, "alternatives": [dict(TASK)]})
    assert result["status"] == "ready_for_payment"
    assert sum(e.get("message") == "Essai d’un autre site" for e in events) == 1


def test_page_identity_preserves_values_blanks_and_duplicate_order():
    from runai.agents.hclient import _page_identity

    original = "https://example.org/checkpoint?city=Paris&choice=1&choice=2&blank="
    assert _page_identity(original) == _page_identity(
        "https://example.org/checkpoint?blank=&choice=1&choice=2&city=Paris",
    )
    for changed in (original.replace("Paris", "Rome"), original.replace("blank=", "other="),
                    original.replace("choice=1&choice=2", "choice=2&choice=1")):
        assert _page_identity(original) != _page_identity(changed)


R7_CHECKPOINT_CASES = json.loads((
    Path(__file__).parent / "fixtures/h_checkpoint_observations.json"
).read_text())["r7_cases"]
_bb_checkpoint = dict(next(row for row in R7_CHECKPOINT_CASES
                           if row["id"] == "hotel-bb-milan-room-list"))
_bb_checkpoint.update(id="hotel-bb-milan-review", ready=True,
                      url=_bb_checkpoint["url"].replace("/en/hotel/milano-sant-ambrogio",
                                                        "/booking/review"))
_bb_checkpoint.pop("gate")
R7_CHECKPOINT_CASES.append(_bb_checkpoint)


def r7_checkpoint_task(row):
    builder = {"hotel": hotel_builder, "registration": registration_builder}[row["builder"]]
    trip = {"race": {"name": row["race_name"], "city": row["city"], "country": row["country"],
                     "race_date": row["race_date"], "distance_km": 42.195, "edition": "2027",
                     "official_url": "https://www.wizzairmilanomarathon.it/",
                     "registration_url": row.get("registration_url")},
            "origin_city": "Paris", "arrival_date": row["arrival_date"],
            "departure_date": row["departure_date"], "travelers": 1, "nights": 2}
    task = builder.build_task(trip, today=date(2026, 11, 9))
    task = next(candidate for candidate in [task, *task.get("alternatives", [])]
                if candidate["site_name"] == row["site_name"])
    return {key: value for key, value in task.items() if key != "alternatives"}


@pytest.mark.parametrize("row", R7_CHECKPOINT_CASES, ids=lambda row: row["id"])
@pytest.mark.parametrize("mutation", [None, "wrong_date", "missing_frame", "missing_selection",
                                     "wrong_city", "wrong_party", "different_query"])
def test_r7_builder_checkpoint_observations(row, mutation, monkeypatch):
    monkeypatch.delitem(sys.modules, "runai.agents.site_policy")
    task = r7_checkpoint_task(row)
    verification = dict(row["verification"])
    if mutation == "wrong_date":
        verification["race_date" if row["builder"] == "registration" else "arrival_date"] = "2027-01-01"
    if mutation == "missing_selection":
        verification["selected"] = False
    if mutation == "wrong_city" and row["builder"] == "hotel":
        verification["city"] = "Berlin"
    if mutation == "wrong_party" and row["builder"] == "hotel":
        verification["travelers"] = 2
    event = observation()
    event["data"]["metadata"] = {"url": row["url"], "title": "Synthetic checkpoint"}
    if mutation == "missing_frame":
        event["data"].pop("image")
    answer = {"status": "ready_for_payment", "handoff_url": row.get("answer_url", row["url"]),
              "reached_step": "Safe public checkpoint", "blocker": None,
              "verification": verification}
    if mutation == "different_query":
        answer["handoff_url"] += "&different=1"
    result, _ = run(Provider(events=[event], answer=answer), task)
    ready = row["ready"] and (mutation is None or (
        row["builder"] == "registration" and mutation in {"wrong_city", "wrong_party"}
    ))
    assert (result["status"] == "ready_for_payment") is ready, result
    if row.get("gate"):
        assert row["gate"] in repr(result["steps"])
    if mutation == "missing_frame":
        assert "checkpoint_frame" in repr(result["steps"])


@pytest.mark.parametrize("row", [row for row in R7_CHECKPOINT_CASES if "answer_url" in row],
                         ids=lambda row: row["id"])
def test_r7_query_order_reproduces_handoff_observed_gate(row, monkeypatch):
    from runai.agents.scrub import scrub_url

    monkeypatch.delitem(sys.modules, "runai.agents.site_policy")
    monkeypatch.setattr("runai.agents.hclient._page_identity", scrub_url)
    event = observation()
    event["data"]["metadata"] = {"url": row["url"], "title": "Synthetic checkpoint"}
    answer = {"status": "ready_for_payment", "handoff_url": row["answer_url"],
              "reached_step": "Safe public checkpoint", "blocker": None,
              "verification": row["verification"]}
    result, _ = run(Provider(events=[event], answer=answer), r7_checkpoint_task(row))
    assert result["status"] == "blocked"
    assert 'verify_failed: ["handoff_observed"]' in result["steps"]


@pytest.mark.parametrize("queued", [False, True])
def test_heartbeat_waits_for_observation_gap_and_skips_queued_or_terminal(monkeypatch, queued):
    now = 0
    polls = iter([0, 19, 21, 42])
    events = [] if queued else [blank_observation(HANDOFF)]
    state = "queued" if queued else "running"
    provider = CheckpointProvider([
        batch(*events, state=state), batch(*events, state=state),
        batch(state=state), batch(state="completed", answer=ANSWER),
    ])

    def handle(request):
        nonlocal now
        if request.url.path.endswith("/changes"):
            now = next(polls)
        return provider(request)

    monkeypatch.setattr("runai.agents.hclient.time.monotonic", lambda: now)
    _, emitted = run(handle)
    assert not any("l'agent lit la page" in event.get("message", "") for event in emitted)
