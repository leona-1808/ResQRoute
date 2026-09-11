"""
routing/dynamic_reroute.py

Simulates a traffic change and checks whether the currently selected
route/hospital is still optimal. If not, reroutes.

Two ways to simulate a change (both supported):
  1. Change the time context (e.g. hour shifts from 9am to 6pm rush hour)
  2. Manually spike congestion on specific roads (e.g. an accident/jam)
"""

import pandas as pd

from routing.graph_builder import build_graph_from_roads
from routing.dijkstra_route import (
    load_model,
    simulate_current_traffic,
    predict_travel_times,
    apply_predictions_to_graph,
    find_fastest_route,
)
from routing.hospital_selector import select_optimal_hospital


def simulate_traffic_spike(snapshot_df, road_ids, density_boost=0.4):
    """
    Manually spikes traffic_density (and derived avg_speed/signal_delay)
    on specific roads, e.g. to simulate an accident or sudden jam.
    """
    df = snapshot_df.copy()
    mask = df["road_id"].isin(road_ids)

    df.loc[mask, "traffic_density"] = (df.loc[mask, "traffic_density"] + density_boost).clip(upper=1.0)
    df.loc[mask, "avg_speed"] = (df.loc[mask, "avg_speed"] * (1 - density_boost)).clip(lower=5)
    df.loc[mask, "signal_delay_min"] = df.loc[mask, "signal_delay_min"] + (density_boost * 3)
    df.loc[mask, "vehicle_count"] = (df.loc[mask, "vehicle_count"] * 1.5).astype(int)

    return df


def check_and_reroute(emergency_node, current_route, current_hospital_id,
                       hospitals_path="data/synthetic/hospitals.csv",
                       new_hour=None, new_day=None, spike_road_ids=None,
                       seed=None):
    """
    Re-predicts travel times under new conditions (time change and/or a
    manual congestion spike), then re-runs hospital selection.
    Compares against the currently assigned hospital/route and reports
    whether a reroute is needed.
    """
    model, feature_cols = load_model()
    G = build_graph_from_roads()

    # Build the new snapshot
    hour = new_hour if new_hour is not None else 9
    day = new_day if new_day is not None else "Mon"
    snapshot = simulate_current_traffic(hour=hour, day=day, seed=seed)

    if spike_road_ids:
        snapshot = simulate_traffic_spike(snapshot, spike_road_ids)

    predictions = predict_travel_times(snapshot, model, feature_cols)
    G = apply_predictions_to_graph(G, predictions)

    # Re-run hospital selection under new conditions
    hospitals = pd.read_csv(hospitals_path)
    results = []
    for _, hospital in hospitals.iterrows():
        target_node = hospital["node_location"]
        path, total_time = find_fastest_route(G, emergency_node, target_node)
        results.append({
            "hospital_id": hospital["hospital_id"],
            "name": hospital["name"],
            "route": path,
            "predicted_travel_time": total_time,
        })
    results.sort(key=lambda r: r["predicted_travel_time"])
    new_best = results[0]

    # Also recompute time for the CURRENT route specifically (roads may
    # now be slower even if the same hospital is still best)
    current_route_time = 0.0
    for i in range(len(current_route) - 1):
        u, v = current_route[i], current_route[i + 1]
        current_route_time += G[u][v]["weight"]

    reroute_needed = new_best["hospital_id"] != current_hospital_id

    return {
        "reroute_needed": reroute_needed,
        "current_hospital_id": current_hospital_id,
        "current_route_time_now": current_route_time,
        "new_best": new_best,
        "all_results": results,
    }


if __name__ == "__main__":
    emergency_node = "A"

    # Step 1: original decision (matches hospital_selector.py demo)
    original_best, _ = select_optimal_hospital(emergency_node, hour=9, day="Mon", seed=1)
    print("ORIGINAL DECISION")
    print(f"  Hospital: {original_best['hospital_id']} ({original_best['name']})")
    print(f"  Route: {' -> '.join(original_best['route'])}")
    print(f"  Predicted time: {original_best['predicted_travel_time']:.2f} min\n")

    # Step 2: simulate a traffic change — accident/jam on the current route
    current_route_road_ids = ["R07", "R08"]  # A-D and D-G, matches H2's route
    print(f"SIMULATING: traffic jam on roads {current_route_road_ids}\n")

    outcome = check_and_reroute(
        emergency_node=emergency_node,
        current_route=original_best["route"],
        current_hospital_id=original_best["hospital_id"],
        new_hour=9,
        new_day="Mon",
        spike_road_ids=current_route_road_ids,
        seed=1,
    )

    print("ALL OPTIONS AFTER TRAFFIC CHANGE:")
    for r in outcome["all_results"]:
        route_str = " -> ".join(r["route"])
        print(f"  {r['hospital_id']}: {route_str} | {r['predicted_travel_time']:.2f} min")

    print(f"\nCurrent route ({' -> '.join(original_best['route'])}) now takes: "
          f"{outcome['current_route_time_now']:.2f} min")

    if outcome["reroute_needed"]:
        nb = outcome["new_best"]
        print(f"\n>>> REROUTE TRIGGERED <<<")
        print(f"New optimal hospital: {nb['hospital_id']} ({nb['name']})")
        print(f"New route: {' -> '.join(nb['route'])}")
        print(f"New predicted time: {nb['predicted_travel_time']:.2f} min")
    else:
        print(f"\nNo reroute needed. {outcome['current_hospital_id']} is still optimal, "
              f"though travel time may have changed.")