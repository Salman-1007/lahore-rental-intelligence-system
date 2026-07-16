"""Integration tests for `LocationRepository`, including fuzzy search."""

from app.models.location import Location, LocationLevel
from app.repositories.location_repository import LocationRepository


def test_get_by_exact_name_case_insensitive(db_session) -> None:
    """Exact-name lookup should ignore case."""
    repo = LocationRepository(db_session)
    repo.add(Location(name="Mustafa Town", level=LocationLevel.TOWN))

    found = repo.get_by_exact_name("mustafa town")
    assert found is not None
    assert found.name == "Mustafa Town"


def test_get_children_returns_only_direct_children(db_session) -> None:
    """`get_children` should return direct children, not grandchildren."""
    repo = LocationRepository(db_session)
    city = repo.add(Location(name="Lahore", level=LocationLevel.CITY))
    town = repo.add(Location(name="DHA", level=LocationLevel.TOWN, parent_id=city.id))
    repo.add(Location(name="Phase 5", level=LocationLevel.PHASE, parent_id=town.id))

    children = repo.get_children(city.id)
    assert len(children) == 1
    assert children[0].name == "DHA"


def test_add_alias_and_fuzzy_search_resolves_via_alias(db_session) -> None:
    """A fuzzy search on an alias should resolve to the canonical location."""
    repo = LocationRepository(db_session)
    location = repo.add(Location(name="Defence Housing Authority", level=LocationLevel.TOWN))
    repo.add_alias(location, "DHA")
    repo.add_alias(location, "Defence")

    results = repo.fuzzy_search("DHA Lahore", limit=5, score_cutoff=50)
    assert any(loc.id == location.id for loc in results)


def test_fuzzy_search_returns_empty_for_no_locations(db_session) -> None:
    """Fuzzy search against an empty table should not error, just return []."""
    repo = LocationRepository(db_session)
    assert repo.fuzzy_search("anything") == []
