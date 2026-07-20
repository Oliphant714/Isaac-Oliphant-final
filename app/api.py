"""
Flask REST API for the D&D Encounter Tracker.

Routes are thin wrappers around app.encounter - they parse/validate the
request, call into the core logic, and serialize the response. Keeping
routes thin is what makes app.encounter unit-testable without Flask.
"""
import os
from flask import Flask, jsonify, request, send_from_directory

from app.encounter import EncounterStore, InvalidCombatantError

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> Flask:
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
    store = EncounterStore()

    @app.errorhandler(InvalidCombatantError)
    def handle_invalid(err):
        return jsonify({"error": str(err)}), 400

    @app.route("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/encounters", methods=["GET"])
    def list_encounters():
        return jsonify([e.to_dict() for e in store.list_all()])

    @app.route("/encounters", methods=["POST"])
    def create_encounter():
        body = request.get_json(force=True) or {}
        name = body.get("name")
        if not name:
            return jsonify({"error": "name is required"}), 400
        encounter = store.create(name=name)
        return jsonify(encounter.to_dict()), 201

    @app.route("/encounters/<encounter_id>", methods=["GET"])
    def get_encounter(encounter_id):
        encounter = store.get(encounter_id)
        return jsonify(encounter.to_dict())

    @app.route("/encounters/<encounter_id>", methods=["DELETE"])
    def delete_encounter(encounter_id):
        store.delete(encounter_id)
        return "", 204

    @app.route("/encounters/<encounter_id>/combatants", methods=["POST"])
    def add_combatant(encounter_id):
        encounter = store.get(encounter_id)
        body = request.get_json(force=True) or {}
        required = ["name", "initiative", "max_hp"]
        missing = [f for f in required if f not in body]
        if missing:
            return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400
        combatant = encounter.add_combatant(
            name=body["name"],
            initiative=int(body["initiative"]),
            max_hp=int(body["max_hp"]),
            is_pc=bool(body.get("is_pc", False)),
        )
        return jsonify(combatant.to_dict()), 201

    @app.route("/encounters/<encounter_id>/combatants/<combatant_id>", methods=["DELETE"])
    def remove_combatant(encounter_id, combatant_id):
        encounter = store.get(encounter_id)
        encounter.remove_combatant(combatant_id)
        return "", 204

    @app.route("/encounters/<encounter_id>/combatants/<combatant_id>/damage", methods=["POST"])
    def damage_combatant(encounter_id, combatant_id):
        encounter = store.get(encounter_id)
        combatant = encounter.get_combatant(combatant_id)
        body = request.get_json(force=True) or {}
        amount = int(body.get("amount", 0))
        new_hp = combatant.apply_damage(amount)
        return jsonify({"id": combatant.id, "current_hp": new_hp, "is_alive": combatant.is_alive})

    @app.route("/encounters/<encounter_id>/combatants/<combatant_id>/heal", methods=["POST"])
    def heal_combatant(encounter_id, combatant_id):
        encounter = store.get(encounter_id)
        combatant = encounter.get_combatant(combatant_id)
        body = request.get_json(force=True) or {}
        amount = int(body.get("amount", 0))
        new_hp = combatant.apply_healing(amount)
        return jsonify({"id": combatant.id, "current_hp": new_hp, "is_alive": combatant.is_alive})

    @app.route("/encounters/<encounter_id>/next-turn", methods=["POST"])
    def next_turn(encounter_id):
        encounter = store.get(encounter_id)
        encounter.next_turn()
        return jsonify(encounter.to_dict())

    return app


# Used by `flask run` / gunicorn / `python -m app.api`
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
