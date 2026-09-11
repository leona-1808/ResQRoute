"""
routing/hospital_selector.py

Given an emergency location, runs Dijkstra (on predicted travel time)
to every hospital and picks the one with the lowest predicted travel time.
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


def select_optimal_hospital(emergency_node, hospitals_path="data/synthetic/hospitals.csv",
                             hour=8, day="Mon", seed=None):
    """
    Returns the best hospital (lowest predicted travel time), plus the
    route and time to every hospital, so you can show the comparison.
    """
    hospitals = pd.read_csv(hospitals_path)

    G = build_graph_from_roads()
    model, feature_cols = load_model()

    snapshot = simulate_current_traffic(hour=hour, day=day, seed=seed)
    predictions = predict_travel_times(snapshot, model, feature_cols)
    G = apply_predictions_to_graph(G, predictions)

    results = []
    for _, hospital in hospitals.iterrows():
        target_node = hospital["node_location"]
        path, total_time = find_fastest_route(G, emergency_node, target_node)
        results.append({
            "hospital_id": hospital["hospital_id"],
            "name": hospital["name"],
            "node_location": target_node,
            "route": path,
            "predicted_travel_time": total_time,
        })

    results.sort(key=lambda r: r["predicted_travel_time"])
    best = results[0]

    return best, results


if __name__ == "__main__":
    emergency_node = "A"
    best, all_results = select_optimal_hospital(emergency_node, hour=9, day="Mon", seed=1)

    print(f"Emergency location: {emergency_node}\n")
    print("All hospital options:")
    for r in all_results:
        route_str = " -> ".join(r["route"])
        print(f"  {r['hospital_id']} ({r['name']}): {route_str} | {r['predicted_travel_time']:.2f} min")

    print(f"\n==> Optimal hospital: {best['hospital_id']} ({best['name']})")
    print(f"    Route: {' -> '.join(best['route'])}")
    print(f"    Predicted travel time: {best['predicted_travel_time']:.2f} minutes")