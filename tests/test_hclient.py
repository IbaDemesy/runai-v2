import asyncio
import base64
import json

import httpx
import pytest

from runai.agents.hclient import GUARDRAILS, HAgentRunner, HUnavailable
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
}
ANSWER = {
    "status": "ready_for_payment", "handoff_url": HANDOFF,
    "reached_step": "Registration information found; stopped before any form.", "blocker": None,
}


def observation(image=None):
    return {
        "type": "AgentEvent", "timestamp": "2026-11-08T20:00:00Z",
        "data": {
            "kind": "observation_event", "type": "web",
            "metadata": {"url": HANDOFF + "?session=private&distance=42", "title": "Race entry"},
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
        async def emit(event):
            emitted.append(event)

        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            runner = HAgentRunner("test-api-key", base_url=API, client=client, poll_s=0, **kwargs)
            result = await runner.run(task or TASK, emit)
            assert not client.is_closed
            return result

    return asyncio.run(execute()), emitted


def test_run_emits_real_api_frames_and_only_documented_public_share():
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
    assert result["final_url"] == HANDOFF + "?distance=42"
    assert result["live_view_url"] == PUBLIC_SHARE
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
    assert body["max_steps"] == 30 and body["max_time_s"] == 600
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
    "No form submitted, but I paid", "No account created and booking completed",
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
    assert result["status"] == "blocked" and "Captcha" in result["error"]


def test_provider_terminal_failure_is_not_success():
    result, _ = run(Provider(status="failed"))
    assert result["status"] == "failed" and result["error"] == "H session failed"


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
    assert scrub_url(PUBLIC_SHARE) == PUBLIC_SHARE


@pytest.mark.parametrize("path", [
    "/session/synthetic-private-token", "/entry/auth/synthetic-token", "/token=synthetic-value",
    "/entry/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", "/entry/runner%40example.org",
    "/entry/a1b2c3d4e5f6-synthetic-a7b8c9d0e1f2", "/entry/+33-6-12-34-56-78",
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


@pytest.mark.parametrize("url", [
    "https://in.njuko.com/wizz-air-milano-marathon-20271776152378557",
    "https://inscripciones.rpmsports.es/es/evento/zurich-marato-barcelona-2027/my-registration",
    "https://race.example.org/northern-city-road-marathon-2028-04-02",
])
def test_public_word_slugs_work_as_start_handoff_and_progress_urls(url):
    assert scrub_url(url) == url
    message = "Read " + url + " then stop"
    assert scrub_text(message) == message
    provider = Provider(
        answer={**ANSWER, "handoff_url": url},
        events=[{"type": "AgentEvent", "data": {"kind": "policy_event", "content": message}}],
    )
    result, events = run(provider, task={**TASK, "start_url": url})
    assert result["status"] == "ready_for_payment"
    assert result["start_url"] == result["handoff_url"] == url
    assert any(e.get("message") == message for e in events)
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
    provider = Provider(
        answer={**ANSWER, "handoff_url": HANDOFF + "?token=secret&distance=42#private",
                "reached_step": "runner@example.org +33 6 12 34 56 78 test-api-key"},
        events=[{"type": "AgentEvent", "data": {
            "kind": "policy_event", "content": "runner@example.org test-api-key",
        }}, observation()],
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
                "status": "running", "new_events": [], "metrics": {"steps": 50},
            })
        return provider(request)

    result, _ = run(capped, task={**TASK, "max_steps": 500})
    assert result["status"] == "failed" and "step limit" in result["error"]
    assert json.loads(provider.requests[0].content)["max_steps"] == 50
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
])
def test_authenticated_screenshot_resource_redirect_drops_bearer(source):
    provider = Provider(events=[observation({
        "type": "url", "source": source, "media_type": "image/png",
    })])

    def image_request(request):
        if request.url.path.endswith("/resources/screenshots/frame.png"):
            assert request.headers["Authorization"] == "Bearer test-api-key"
            return httpx.Response(302, headers={"location": "https://images.example.org/frame.png"})
        if request.url.host == "images.example.org":
            assert not request.headers.get("Authorization")
            return httpx.Response(200, content=IMAGE)
        return provider(request)

    result, events = run(image_request)
    assert result["status"] == "ready_for_payment"
    assert any(e["type"] == "live_frame" for e in events)


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
    assert result["status"] == "ready_for_payment" and polls == 2
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


def test_progress_uses_action_names_without_echoing_user_prompt_or_tool_arguments():
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
    assert result["status"] == "ready_for_payment"
    assert "H browser action: scroll_web" in result["steps"]
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
                    "new_events": [],
                })
            raise AssertionError("Unexpected concurrent mock request")

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            runner = HAgentRunner("test-key", client=client)
            results = await asyncio.gather(runner.run(TASK), runner.run(TASK), runner.run(TASK))
        assert len({r["handoff_url"] for r in results}) == 3
        assert all(r["status"] == "ready_for_payment" for r in results)
        assert len(sessions) == 3

    asyncio.run(execute())
