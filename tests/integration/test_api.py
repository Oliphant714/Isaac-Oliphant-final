import pytest
from app.api import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_create_encounter(client):
    res = client.post("/encounters", json={"name": "Goblin Ambush"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["name"] == "Goblin Ambush"
    assert body["round"] == 1
    assert body["combatants"] == []


def test_create_encounter_without_name_fails(client):
    res = client.post("/encounters", json={})
    assert res.status_code == 400


def test_full_encounter_flow(client):
    # Create an encounter
    res = client.post("/encounters", json={"name": "Boss Fight"})
    encounter_id = res.get_json()["id"]

    # Add two combatants
    res = client.post(
        f"/encounters/{encounter_id}/combatants",
        json={"name": "Hero", "initiative": 20, "max_hp": 30, "is_pc": True},
    )
    assert res.status_code == 201
    hero_id = res.get_json()["id"]

    res = client.post(
        f"/encounters/{encounter_id}/combatants",
        json={"name": "Dragon", "initiative": 15, "max_hp": 100},
    )
    dragon_id = res.get_json()["id"]

    # Fetch the encounter and check turn order (Hero has higher initiative)
    res = client.get(f"/encounters/{encounter_id}")
    body = res.get_json()
    assert body["current_turn"]["name"] == "Hero"

    # Damage the dragon
    res = client.post(f"/encounters/{encounter_id}/combatants/{dragon_id}/damage", json={"amount": 40})
    assert res.status_code == 200
    assert res.get_json()["current_hp"] == 60

    # Advance turn
    res = client.post(f"/encounters/{encounter_id}/next-turn")
    assert res.get_json()["current_turn"]["name"] == "Dragon"

    # Heal the hero
    res = client.post(f"/encounters/{encounter_id}/combatants/{hero_id}/heal", json={"amount": 5})
    assert res.status_code == 200


def test_add_combatant_missing_fields_fails(client):
    res = client.post("/encounters", json={"name": "Test"})
    encounter_id = res.get_json()["id"]

    res = client.post(f"/encounters/{encounter_id}/combatants", json={"name": "NoStats"})
    assert res.status_code == 400


def test_get_nonexistent_encounter_returns_400(client):
    res = client.get("/encounters/does-not-exist")
    assert res.status_code == 400


def test_delete_encounter(client):
    res = client.post("/encounters", json={"name": "Temp"})
    encounter_id = res.get_json()["id"]

    res = client.delete(f"/encounters/{encounter_id}")
    assert res.status_code == 204

    res = client.get(f"/encounters/{encounter_id}")
    assert res.status_code == 400


def test_list_encounters(client):
    client.post("/encounters", json={"name": "One"})
    client.post("/encounters", json={"name": "Two"})

    res = client.get("/encounters")
    assert res.status_code == 200
    assert len(res.get_json()) == 2
