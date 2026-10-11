"""M2: public taxonomy & inventory endpoints (interest tree, channels, geos, companies)."""
import asyncio

from app.models.inventory import Channel, ChannelCategory, Company, Geo, GeoType, InterestSegment
from tests.conftest import TestSessionLocal


def seed_minimal() -> None:
    async def go():
        async with TestSessionLocal() as s:
            sports = InterestSegment(name="Sports", reach_households=52_000_000)
            s.add(sports)
            await s.flush()
            s.add_all([
                InterestSegment(parent_id=sports.id, name="American Football", reach_households=20_000_000),
                InterestSegment(parent_id=sports.id, name="Soccer", reach_households=12_000_000),
            ])
            s.add_all([
                Channel(name="Peak TV", category=ChannelCategory.entertainment,
                        reach_households=44_000_000, base_cpm_micros=28_000_000, is_premium=True),
                Channel(name="SportsCenter Live", category=ChannelCategory.sports,
                        reach_households=13_000_000, base_cpm_micros=38_000_000, is_premium=True),
            ])
            s.add_all([
                Geo(type=GeoType.state, code="CA", name="California", households=19_000_000),
                Geo(type=GeoType.city, code="LA,CA", name="Los Angeles", households=5_000_000),
            ])
            s.add(Company(domain="acme.com", name="Acme Corp", industry="software", size_bucket="51-200"))
            await s.commit()

    asyncio.run(go())


def test_interest_segments_tree(client):
    seed_minimal()
    tree = client.get("/api/v1/interest-segments").json()
    assert isinstance(tree, list) and len(tree) == 1
    root = tree[0]
    assert root["name"] == "Sports"
    assert root["reach_households"] == 52_000_000
    child_names = {c["name"] for c in root["children"]}
    assert child_names == {"American Football", "Soccer"}
    assert all(c["reach_households"] > 0 for c in root["children"])


def test_channels_total_and_filter(client):
    seed_minimal()
    r = client.get("/api/v1/channels").json()
    assert r["total_count"] == 2
    assert r["all_apps_reach_households"] == 57_000_000  # 44M + 13M
    # category filter
    sports = client.get("/api/v1/channels?category=sports").json()
    assert [c["name"] for c in sports["items"]] == ["SportsCenter Live"]
    # search
    peak = client.get("/api/v1/channels?q=peak").json()
    assert [c["name"] for c in peak["items"]] == ["Peak TV"]


def test_geos_search(client):
    seed_minimal()
    calif = client.get("/api/v1/geos/search?q=calif").json()
    assert any(g["name"] == "California" and g["type"] == "state" for g in calif)
    la = client.get("/api/v1/geos/search?q=los").json()
    assert any(g["name"] == "Los Angeles" for g in la)
    only_states = client.get("/api/v1/geos/search?q=a&type=state").json()
    assert all(g["type"] == "state" for g in only_states)


def test_companies_search(client):
    seed_minimal()
    rows = client.get("/api/v1/companies/search?q=acme").json()
    assert [c["name"] for c in rows] == ["Acme Corp"]
