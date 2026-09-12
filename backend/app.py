"""
backend/app.py

Flask entry point. Exposes the emergency pipeline (ML prediction ->
routing -> hospital selection -> optional reroute check) as a JSON API,
and persists each emergency to a SQLite database via SQLAlchemy.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, request, render_template

from routing.hospital_selector import select_optimal_hospital
from routing.dynamic_reroute import check_and_reroute
from routing.graph_builder import build_graph_from_roads
from routing.dijkstra_route import get_road_ids_for_route
from backend.models.db_models import db, Emergency

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)

database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Render's Postgres URLs start with postgres://, but SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'database.db')}"

db.init_app(app)

with app.app_context():
    db.create_all()

# in-memory pointer to the most recent emergency's DB row + working state,
# so /api/traffic/simulate knows what it's rerouting relative to
current_emergency = {}


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/emergency", methods=["POST"])
def create_emergency():
    data = request.get_json(force=True)
    node = data.get("node", "A")
    hour = data.get("hour", 9)
    day = data.get("day", "Mon")

    best, all_results = select_optimal_hospital(node, hour=hour, day=day, seed=1)

    G = build_graph_from_roads()
    green_corridor_roads = get_road_ids_for_route(G, best["route"])

    # save to database
    record = Emergency(
        emergency_node=node,
        hour=hour,
        day=day,
        hospital_id=best["hospital_id"],
        hospital_name=best["name"],
        route="->".join(best["route"]),
        predicted_travel_time=best["predicted_travel_time"],
        rerouted=False,
    )
    db.session.add(record)
    db.session.commit()

    current_emergency.clear()
    current_emergency.update({
        "db_id": record.id,
        "emergency_node": node,
        "hour": hour,
        "day": day,
        "hospital_id": best["hospital_id"],
        "route": best["route"],
        "predicted_travel_time": best["predicted_travel_time"],
    })

    return jsonify({
        "emergency_node": node,
        "green_corridor_roads": green_corridor_roads,
        "best_hospital": {
            "id": best["hospital_id"],
            "name": best["name"],
            "route": best["route"],
            "predicted_travel_time": round(best["predicted_travel_time"], 2),
        },
        "all_options": [
            {
                "id": r["hospital_id"],
                "name": r["name"],
                "route": r["route"],
                "predicted_travel_time": round(r["predicted_travel_time"], 2),
            }
            for r in all_results
        ],
    })


def _apply_reroute_outcome(outcome):
    """Shared logic: if a reroute happened, update both the in-memory
    pointer and the corresponding database row."""
    G = build_graph_from_roads()
    green_corridor_roads = get_road_ids_for_route(G, outcome["new_best"]["route"])

    if outcome["reroute_needed"]:
        nb = outcome["new_best"]
        current_emergency.update({
            "hospital_id": nb["hospital_id"],
            "route": nb["route"],
            "predicted_travel_time": nb["predicted_travel_time"],
        })

        record = Emergency.query.get(current_emergency.get("db_id"))
        if record:
            record.hospital_id = nb["hospital_id"]
            record.hospital_name = nb["name"]
            record.route = "->".join(nb["route"])
            record.predicted_travel_time = nb["predicted_travel_time"]
            record.rerouted = True
            db.session.commit()

    return green_corridor_roads


@app.route("/api/traffic/simulate", methods=["POST"])
def simulate_traffic_change():
    if not current_emergency:
        return jsonify({"error": "No active emergency. Call /api/emergency first."}), 400

    data = request.get_json(force=True)
    spike_roads = data.get("spike_roads", [])
    hour = data.get("hour", current_emergency["hour"])
    day = data.get("day", current_emergency["day"])

    outcome = check_and_reroute(
        emergency_node=current_emergency["emergency_node"],
        current_route=current_emergency["route"],
        current_hospital_id=current_emergency["hospital_id"],
        new_hour=hour,
        new_day=day,
        spike_road_ids=spike_roads,
        seed=1,
    )

    green_corridor_roads = _apply_reroute_outcome(outcome)

    return jsonify({
        "reroute_needed": outcome["reroute_needed"],
        "current_route_time_now": round(outcome["current_route_time_now"], 2),
        "green_corridor_roads": green_corridor_roads,
        "new_best_hospital": {
            "id": outcome["new_best"]["hospital_id"],
            "name": outcome["new_best"]["name"],
            "route": outcome["new_best"]["route"],
            "predicted_travel_time": round(outcome["new_best"]["predicted_travel_time"], 2),
        },
        "all_options": [
            {
                "id": r["hospital_id"],
                "name": r["name"],
                "route": r["route"],
                "predicted_travel_time": round(r["predicted_travel_time"], 2),
            }
            for r in outcome["all_results"]
        ],
    })


@app.route("/api/traffic/jam-current-route", methods=["POST"])
def jam_current_route():
    if not current_emergency:
        return jsonify({"error": "No active emergency. Call /api/emergency first."}), 400

    G = build_graph_from_roads()
    current_route_roads = get_road_ids_for_route(G, current_emergency["route"])

    outcome = check_and_reroute(
        emergency_node=current_emergency["emergency_node"],
        current_route=current_emergency["route"],
        current_hospital_id=current_emergency["hospital_id"],
        new_hour=current_emergency["hour"],
        new_day=current_emergency["day"],
        spike_road_ids=current_route_roads,
        seed=1,
    )

    green_corridor_roads = _apply_reroute_outcome(outcome)

    return jsonify({
        "jammed_roads": current_route_roads,
        "reroute_needed": outcome["reroute_needed"],
        "current_route_time_now": round(outcome["current_route_time_now"], 2),
        "green_corridor_roads": green_corridor_roads,
        "new_best_hospital": {
            "id": outcome["new_best"]["hospital_id"],
            "name": outcome["new_best"]["name"],
            "route": outcome["new_best"]["route"],
            "predicted_travel_time": round(outcome["new_best"]["predicted_travel_time"], 2),
        },
        "all_options": [
            {
                "id": r["hospital_id"],
                "name": r["name"],
                "route": r["route"],
                "predicted_travel_time": round(r["predicted_travel_time"], 2),
            }
            for r in outcome["all_results"]
        ],
    })


@app.route("/api/history", methods=["GET"])
def get_history():
    """Returns all past emergencies, most recent first."""
    records = Emergency.query.order_by(Emergency.created_at.desc()).all()
    return jsonify([r.to_dict() for r in records])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
    