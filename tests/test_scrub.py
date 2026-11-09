from urllib.parse import quote

import pytest

from runai.agents.scrub import public_profile_context, scrub_profile, scrub_text, scrub_url

OMIO = ("https://www.omio.com/links/626fa8a9-0000-4000-8000-000000000000"
        "?departurePosTerm=Paris&arrivalPosTerm=Frankfurt&departureDate=2027-10-29"
        "&returnDate=2027-11-01&adults=1")
GOOGLE_FLIGHTS = (
    "https://www.google.com/travel/flights/booking?"
    "tfs=CBwQAhooEgoyMDI3LTAxLTI4agwIAhIIL20vMDVxdGpyDAgDEggvbS8wcjBsbRooEgoyMDI3LTAxLTMw"
    "agwIAxIIL20vMHIwbG1yDAgCEggvbS8wNXF0akABSAFwAYIBCwj___________8BmAEB&tfu=EgYIABAAGAA&hl=en"
)
OMIO_REDIRECT = OMIO.replace(
    "/links/626fa8a9-0000-4000-8000-000000000000",
    "/app/search-frontend/results/626fa8a9000040008000000000000000/train",
)


@pytest.mark.parametrize("host", ["www.omio.com", "omio.com", "www.omio.fr", "omio.fr",
                                  "www.omio.de", "omio.de"])
@pytest.mark.parametrize("mode", ["train", "bus", "flight"])
def test_public_omio_redirect_result_links(host, mode):
    url = OMIO_REDIRECT.replace("www.omio.com", host).replace("/train?", f"/{mode}?")
    assert scrub_url(url) == url
    assert scrub_url(url + "&utm_source=test&gclid=test&tracking=test") == url
    assert scrub_text(url) == url


@pytest.mark.parametrize("url", [
    OMIO_REDIRECT.replace("www.omio.com", "example.org"),
    OMIO_REDIRECT.replace("www.omio.com", "www.omio.com.evil.org"),
    OMIO_REDIRECT.replace("/results/", "/private/"),
    OMIO_REDIRECT.replace("/search-frontend/", "/other-frontend/"),
    OMIO_REDIRECT.replace("/train?", "/taxi?"),
    OMIO_REDIRECT.replace("/train?", "/train/extra?"),
    OMIO_REDIRECT.replace("626fa8a9000040008000000000000000", "a1" * 33),
])
def test_omio_redirect_exception_is_strictly_scoped(url):
    assert scrub_url(url) is None


@pytest.mark.parametrize("result_id", ["x", "a1" * 32])
def test_omio_redirect_id_length_boundaries(result_id):
    url = OMIO_REDIRECT.replace("626fa8a9000040008000000000000000", result_id)
    assert scrub_url(url) == url


@pytest.mark.parametrize("host", ["www.google.com", "google.com", "www.google.fr", "google.de"])
@pytest.mark.parametrize("path", ["booking", "search"])
def test_public_google_flights_itinerary_tokens(host, path):
    url = GOOGLE_FLIGHTS.replace("www.google.com", host).replace("/booking?", f"/{path}?")
    assert scrub_url(url) == url
    assert scrub_url(url + "&utm_source=test&gclid=test") == url
    assert scrub_text(url) == url


@pytest.mark.parametrize("url", [
    GOOGLE_FLIGHTS.replace("www.google.com", "example.org"),
    GOOGLE_FLIGHTS.replace("www.google.com", "www.google.com.evil.org"),
    GOOGLE_FLIGHTS.replace("/booking?", "/other?"),
    GOOGLE_FLIGHTS.replace("/booking?", "/booking/extra?"),
    GOOGLE_FLIGHTS.replace("tfs=", "other="),
])
def test_google_itinerary_exception_does_not_widen_other_urls_or_keys(url):
    clean = scrub_url(url)
    assert "CBwQAhoo" not in clean


@pytest.mark.parametrize("key", ["tfs", "tfu"])
@pytest.mark.parametrize("value", ["", "abc+", "abc/", "abc=", "x" * 601])
def test_invalid_google_itinerary_tokens_are_dropped(key, value):
    url = "https://www.google.com/travel/flights/booking"
    assert scrub_url(url + f"?{key}=" + quote(value, safe="") + "&hl=en") == url + "?hl=en"


@pytest.mark.parametrize("value", ["x", "x" * 600])
def test_google_itinerary_token_length_boundaries(value):
    url = "https://www.google.com/travel/flights/search?tfs=" + value
    assert scrub_url(url) == url


def test_public_omio_result_links():
    assert scrub_url(OMIO) == OMIO
    assert scrub_url(OMIO + "&utm_source=test&gclid=test&tracking=test") == OMIO
    assert scrub_text(OMIO) == OMIO


@pytest.mark.parametrize("url", [
    OMIO.replace("www.omio.com", "example.org"),
    OMIO.replace("/links/", "/private/"),
    OMIO.replace("000000000000?", "00000000000z?"),
    OMIO.replace("www.omio.com", "www.omio.com.evil.org"),
])
def test_omio_exception_is_scoped(url):
    assert scrub_url(url) is None


def test_profile_quasi_identifiers_preserve_urls_and_public_context():
    profile = {"city": "Paris", "nationality": "FR", "gender": "F", "country": "France"}
    url = "https://example.org/fr/Paris?country=France"
    assert scrub_profile(url, profile) == url
    assert scrub_profile("Paris France FR F Frankfurt", profile) == (
        "[redacted profile] [redacted profile] [redacted profile] [redacted profile] Frankfurt"
    )
    skip = public_profile_context({"origin_city": "PARIS", "race": {"country": "France"},
                                   "runner_profile": profile})
    assert scrub_profile("Paris France FR", profile, skip) == "Paris France [redacted profile]"
    assert scrub_profile("Paris " + url, profile) == "[redacted profile] " + url


@pytest.mark.parametrize("field", ["full_name", "given_name", "family_name", "email", "phone",
                                    "birth_date", "address_line", "postal_code"])
def test_identifying_values_always_redacted_even_when_public(field):
    value = "Sentinelidentityxyz"
    profile = {field: value}
    assert scrub_profile(value.upper(), profile, {value}) == "[redacted profile]"
    assert scrub_profile("https://example.org/" + value.upper(), profile, {value}) is None


@pytest.mark.parametrize("profile", [{}, {"city": None}, {"city": ""}])
def test_empty_profile_redaction(profile):
    value = {"summary": "Paris", "handoff_url": "https://example.org/fr/Paris", "other": None}
    assert scrub_profile(value, profile) == value


def test_white_label_njuko_public_id():
    url = ("https://in.motionevents-registrations.com/"
           "wizz-air-milano-marathon-20271776152378557?currentPage=form_individual-form")
    assert scrub_url(url) == url
    assert scrub_text(url) == url
    opaque = "https://in.motionevents-registrations.com/w/8a51dd786fba3d1be53c9a97"
    assert scrub_url(opaque) == opaque
    assert scrub_url(opaque.replace("-registrations.com", "-registrations.com.evil.org")) is None


def test_tracking_noise_removed_without_changing_ihg_stay():
    url = "https://www.ihg.com/select-enhance-stay?qCiD=09&qCiMy=062027&qAdlt=2"
    assert scrub_url(url + "&utm_source=example&cm_mmc=example&gclid=example") == url


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
