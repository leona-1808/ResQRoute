"""
routing/graph_builder.py

Builds a NetworkX graph from roads.csv. Edge weights can be either the
raw base_distance_km (for a sanity-check run) or predicted travel time
(once the ML model is wired in — see dijkstra_route.py).
"""

import pandas as pd
import networkx as nx


def build_graph_from_roads(roads_path="data/synthetic/roads.csv"):
    """
    Builds an undirected graph where each road is an edge.
    Initially weighted by base_distance_km. Edge weights get
    overwritten later with predicted travel time.
    """
    roads = pd.read_csv(roads_path)

    G = nx.Graph()

    for _, row in roads.iterrows():
        G.add_edge(
            row["node_from"],
            row["node_to"],
            road_id=row["road_id"],
            distance_km=row["base_distance_km"],
            weight=row["base_distance_km"],  # default weight = distance
        )

    return G


if __name__ == "__main__":
    # quick sanity check when run directly
    G = build_graph_from_roads()
    print("Nodes:", list(G.nodes))
    print("Edges:")
    for u, v, data in G.edges(data=True):
        print(f"  {u} - {v} | road_id={data['road_id']} | weight={data['weight']}")