"""
routing/dijkstra_route.py

Predicts current travel time for every road using the trained ML model,
sets those predictions as edge weights on the graph, then runs Dijkstra
to find the fastest route between two nodes.
"""

import numpy as np
import pandas as pd
import joblib
import networkx as nx

from routing.graph_builder import build_graph_from_roads


def load_model(path="ml/best_model.pkl"):
    bundle = joblib.load(path)
    return bundle["model"], bundle["features"]


def simulate_current_traffic(roads_path="data/synthetic/roads.csv", hour=8, day="Mon", seed=None):
    """
    Simulates a 'right now' traffic snapshot for every road.
    In a real system this would come from live sensors/APIs.
    For the prototype, we generate one plausible reading per road.
    """
    if seed is not None:
        np.random.seed(seed)

    roads = pd.read_csv(roads_path)
    is_rush = hour in [8, 9, 10, 17, 18, 19]
    is_weekend = day in ["Sat", "Sun"]

    rows = []
    for _, road in roads.iterrows():
        base_vehicle_count = np.random.randint(20, 80)
        if is_rush and not is_weekend:
            vehicle_count = base_vehicle_count + np.random.randint(40, 100)
        elif is_weekend:
            vehicle_count = max(5, base_vehicle_count - np.random.randint(10, 30))
        else:
            vehicle_count = base_vehicle_count

        traffic_density = np.clip(vehicle_count / 180 + np.random.normal(0, 0.05), 0.05, 1.0)
        avg_speed = np.clip(60 * (1 - 0.75 * traffic_density) + np.random.normal(0, 3), 8, 60)
        signal_delay = np.clip(np.random.normal(1 + 3 * traffic_density, 0.5), 0.2, 6)

        rows.append({
            "road_id": road["road_id"],
            "node_from": road["node_from"],
            "node_to": road["node_to"],
            "hour": hour,
            "day": day,
            "vehicle_count": int(vehicle_count),
            "traffic_density": round(traffic_density, 3),
            "avg_speed": round(avg_speed, 2),
            "road_length_km": road["base_distance_km"],
            "signal_delay_min": round(signal_delay, 2),
        })

    return pd.DataFrame(rows)


def predict_travel_times(snapshot_df, model, feature_cols):
    """
    Applies the same one-hot encoding used in training, aligns columns,
    and predicts travel time for every road in the snapshot.
    """
    df = pd.get_dummies(snapshot_df, columns=["day"], drop_first=True)

    # make sure all expected feature columns exist (missing day columns = 0)
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0

    X = df[feature_cols]
    predictions = model.predict(X)

    result = snapshot_df.copy()
    result["predicted_travel_time"] = predictions
    return result


def apply_predictions_to_graph(G, predictions_df):
    """
    Overwrites each edge's 'weight' with the model's predicted travel time.
    """
    for _, row in predictions_df.iterrows():
        u, v = row["node_from"], row["node_to"]
        if G.has_edge(u, v):
            G[u][v]["weight"] = row["predicted_travel_time"]
            G[u][v]["predicted_travel_time"] = row["predicted_travel_time"]
    return G


def find_fastest_route(G, source, target):
    path = nx.dijkstra_path(G, source, target, weight="weight")
    total_time = nx.dijkstra_path_length(G, source, target, weight="weight")
    return path, total_time
def get_road_ids_for_route(G, path):
    """
    Given a node path like ['A', 'D', 'G'], returns the list of road_ids
    traversed, so they can be flagged as Green Corridor priority.
    """
    road_ids = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        road_ids.append(G[u][v]["road_id"])
    return road_ids

if __name__ == "__main__":
    G = build_graph_from_roads()
    model, feature_cols = load_model()

    snapshot = simulate_current_traffic(hour=9, day="Mon", seed=1)
    predictions = predict_travel_times(snapshot, model, feature_cols)
    G = apply_predictions_to_graph(G, predictions)

    print("Predicted travel time per road:")
    print(predictions[["road_id", "node_from", "node_to", "predicted_travel_time"]])

    source, target = "A", "I"
    path, total_time = find_fastest_route(G, source, target)
    print(f"\nFastest route from {source} to {target}: {' -> '.join(path)}")
    print(f"Predicted total travel time: {total_time:.2f} minutes")