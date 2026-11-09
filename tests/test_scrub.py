from urllib.parse import quote

import pytest

from runai.agents.scrub import scrub_text, scrub_url


@pytest.mark.parametrize("secret", [
    "4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111",
    "DE89 3704 0044 0532 0130 00", "cvv: 123", "expiry: 12/29",
    "password=sentinel-password", "token=sentinel-token", "runner@example.org",
    "+33 6 12 34 56 78", "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ4In0.signature",
    "Bearer https://private.example.org/key",
])
def test_sensitive_patterns_never_survive(secret):
    assert secret not in scrub_text("Observed " + secret)
    url = "https://race.example.org/entry?value=" + quote(secret)
    assert "value=" not in (scrub_url(url) or "")


@pytest.mark.parametrize("value", [
    "2027-04-04", "EUR 1200", "1 200 €", "42.195 km", "21 km",
    "https://race.example.org/event/1234567890?date=2027-04-04&from=Paris&to=Rome",
    "https://race.example.org/northern-city-marathon-2027",
])
def test_public_context_preserved(value):
    assert scrub_text(value) == value


def test_empty_and_private_urls():
    assert scrub_text(None) == ""
    assert scrub_url(None) is None
    assert scrub_url("https://agp.eu.hcompany.ai/share/api/v1/trajectories/public") is None


@pytest.mark.parametrize("url", [
    "https://in.njuko.com/generali-geneve-marathon-2027-1782304695994",
    "https://in.njuko.com/wizz-air-milano-marathon-20271776152378557",
    "https://in.njuko.com/w/8a51dd786fba3d1be53c9a97",
    "https://www.njuko.net/w/8a51dd786fba3d1be53c9a97",
])
def test_public_njuko_event_ids_are_not_contact_details(url):
    assert scrub_url(url) == url
    assert scrub_text("Race " + url) == "Race " + url
    assert scrub_url(url + "?phone=%2B33+6+12+34+56+78&email=runner%40example.org") == url


@pytest.mark.parametrize("url", [
    "https://in.njuko.com/w/runner@example.org",
    "https://in.njuko.com/w/+33-6-12-34-56-78",
    "https://other.example.org/w/8a51dd786fba3d1be53c9a97",
    "https://in.njuko.com/private/8a51dd786fba3d1be53c9a97",
    "https://in.njuko.com/runner-2027-0612345678901",
    "https://in.njuko.com/runner-0612345678-2027-1782304695994",
    "https://in.njuko.com/hai-sentinel-secret-2027-1782304695994",
])
def test_njuko_exception_does_not_allow_contacts_or_arbitrary_opaque_paths(url):
    assert scrub_url(url) is None
