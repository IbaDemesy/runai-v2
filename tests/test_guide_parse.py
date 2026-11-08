from datetime import date

import pytest

from runai.guide.parse import bare_city, parse_intent

TODAY = date(2026, 9, 1)


@pytest.mark.parametrize(
    "text,distance",
    [
        ("marathon", "marathon"),
        ("semi", "half"),
        ("half marathon", "half"),
        ("10k", "10k"),
        ("trail", "trail"),
        ("ultra marathon", "ultra"),
    ],
)
def test_distances(text, distance):
    assert parse_intent(text, today=TODAY).distance == distance


@pytest.mark.parametrize(
    "text,months",
    [
        ("au printemps", ["2027-03", "2027-04", "2027-05"]),
        ("cet été", ["2027-06", "2027-07", "2027-08"]),
        ("cet ete", ["2027-06", "2027-07", "2027-08"]),
        ("next spring", ["2027-03", "2027-04", "2027-05"]),
        ("this summer", ["2027-06", "2027-07", "2027-08"]),
        ("en avril", ["2027-04"]),
        ("in May", ["2027-05"]),
        ("en hiver", ["2026-12", "2027-01", "2027-02"]),
        ("in May 2028", ["2028-05"]),
    ],
)
def test_months(text, months):
    assert parse_intent(text, today=TODAY).months == months


@pytest.mark.parametrize(
    "text,country,city",
    [
        ("en Italie", "Italy", None),
        ("in Switzerland", "Switzerland", None),
        ("en Suède", "Sweden", None),
        ("in Czechia", "Czechia", None),
        ("Milano", "Italy", "Milan"),
        ("Genève", "Switzerland", "Geneva"),
        ("Barcelone", "Spain", "Barcelona"),
        ("Londres", "United Kingdom", "London"),
        ("Vienna", "Austria", "Vienna"),
        ("Athens", "Greece", "Athens"),
    ],
)
def test_places(text, country, city):
    intent = parse_intent(text, today=TODAY)
    assert (intent.country, intent.city) == (country, city)


def test_named_and_details():
    intent = parse_intent(
        "le semi de Lisbonne depuis Lyon plutôt 3 nuits budget 800 à 2", today=TODAY
    )
    assert (intent.distance, intent.city, intent.named) == ("half", "Lisbon", True)
    assert (intent.origin_city, intent.nights, intent.budget_eur, intent.travelers) == (
        "Lyon",
        3,
        800,
        2,
    )
    assert intent.correction
    assert bare_city("Lyon") == "Lyon"
    assert bare_city("nowhere") is None


@pytest.mark.parametrize("text", ["800 euros", "800 €", "800 eur", "budget 800"])
def test_budget(text):
    assert parse_intent(text, today=TODAY).budget_eur == 800


def test_english_and_empty():
    intent = parse_intent("actually half marathon from Lyon 3 nights 2 people", today=TODAY)
    assert intent.lang == "en" and intent.correction and intent.origin_city == "Lyon"
    assert intent.travelers == 2 and intent.nights == 3
    assert parse_intent("", today=TODAY).distance is None


def test_origin_before_destination():
    intent = parse_intent("from Lyon a half marathon in Lisbon", today=TODAY)
    assert intent.origin_city == "Lyon" and intent.city == "Lisbon"


@pytest.mark.parametrize(
    "text,year", [("Milan marathon 2028", 2028), ("le marathon de Rome 2027", 2027)]
)
def test_explicit_year_without_month(text, year):
    assert parse_intent(text, today=TODAY).year == year


@pytest.mark.parametrize(
    "text,country,city",
    [
        ("a nice trail in Switzerland", "Switzerland", None),
        ("a nice trail", None, None),
        ("un trail à Nice", "France", "Nice"),
        ("a marathon in Nice", "France", "Nice"),
        ("Nice marathon", "France", "Nice"),
        ("Nice marathon in Switzerland", "Switzerland", None),
        ("Paris marathon in Italy", "Italy", None),
    ],
)
def test_city_context_and_explicit_country(text, country, city):
    intent = parse_intent(text, today=TODAY)
    assert (intent.country, intent.city) == (country, city)
