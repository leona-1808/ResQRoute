# AI-Based Dynamic Emergency Route & Green Corridor Optimization System

## Scope (locked)

**Core (must have):**
1. Synthetic road network (3x3 grid, nodes A-I)
2. Synthetic traffic dataset
3. ML travel-time prediction (Linear Regression, Decision Tree, Random Forest — compare and pick best)
4. Dijkstra routing (NetworkX) using **predicted** travel time as edge weight, not raw distance
5. Optimal hospital selection: run Dijkstra to each of 3 hospitals, pick the minimum predicted travel time
6. Dynamic traffic update + rerouting (recompute predictions, check if a better route now exists)
7. Basic Flask API + Leaflet map frontend

**Simplified supporting features:**
8. One ambulance (no fleet/registration system)
9. 3 hospitals (no hospital management system)
10. Green Corridor = simple flag on route's road_ids (`priority: true/false`), no real signal-timing logic
11. SQLite + SQLAlchemy (database-agnostic, easy to swap to MySQL later if ever needed)

**Deferred (only if core works with time to spare):**
12. Power BI dashboard
13. Weather as a model feature
14. Multiple ambulances / priority levels
15. Real city road data

## Why SQLite, not MySQL
No college rubric requires MySQL. SQLAlchemy keeps the persistence layer
database-agnostic, so the prototype stays simple now and could point at
MySQL later with a one-line connection-string change.

## Why "Optimal Hospital Selection" not "Nearest Hospital"
Geographically nearest != fastest to reach. The system picks the hospital
with the lowest *predicted travel time*, which can differ from the
physically closest one when traffic differs across routes. This is a
deliberate design decision worth explaining in interviews/reports.

## Folder structure

```
emergency-route-ai/
├── data/
│   ├── raw/                 # (unused for now — future real dataset)
│   ├── processed/           # cleaned data lands here after preprocessing
│   └── synthetic/
│       ├── roads.csv                  # road network edges + base distance
│       ├── hospitals.csv              # 3 hospitals + node location
│       ├── generate_traffic_data.py   # regenerate traffic_data.csv if needed
│       └── traffic_data.csv           # ML training data (generated)
│
├── ml/
│   ├── preprocess.py        # cleaning + feature engineering
│   ├── train_models.py      # train LR / DT / RF, compare MAE/RMSE/R², save best
│   ├── best_model.pkl       # saved winning model (generated after training)
│   └── predict.py           # loads model, predicts travel time given features
│
├── routing/
│   ├── graph_builder.py     # builds NetworkX graph from roads.csv
│   ├── dijkstra_route.py    # shortest path using predicted weights
│   └── hospital_selector.py # Dijkstra to each hospital, picks minimum
│
├── backend/
│   ├── app.py                  # Flask entry point
│   ├── routes/
│   │   ├── emergency.py        # POST /emergency -> runs full pipeline
│   │   └── traffic.py          # simulate traffic change -> triggers reroute check
│   └── models/
│       └── db_models.py        # SQLAlchemy models: emergencies, roads, traffic_data, hospitals
│
├── frontend/
│   ├── templates/dashboard.html
│   └── static/
│       ├── map.js           # Leaflet map + ambulance marker
│       └── style.css
│
├── notebooks/
│   └── eda.ipynb            # EDA + model comparison (for report screenshots)
│
├── requirements.txt
└── README.md
```

## Data dictionaries

### roads.csv
| column | meaning |
|---|---|
| road_id | unique id, e.g. R01 |
| node_from / node_to | endpoints of the grid (A–I) |
| base_distance_km | static distance, used as fallback + sanity check |

### hospitals.csv
| column | meaning |
|---|---|
| hospital_id | H1, H2, H3 |
| name | display name |
| node_location | which grid node the hospital sits at |
| capacity_beds | flavor field, not used in routing logic |

### traffic_data.csv (ML training data)
| column | meaning |
|---|---|
| road_id | which road this observation is for |
| day / hour | time context (captures rush hour / weekend patterns) |
| vehicle_count | simulated vehicle count |
| traffic_density | 0–1 congestion measure |
| avg_speed | km/h, derived from density |
| road_length_km | joined from roads.csv |
| signal_delay_min | simulated signal wait time |
| **travel_time_minutes** | **target variable** the model predicts |

252 rows generated (12 roads x 7 days x 3 sampled hours/day), with rush-hour
(8-10am, 5-7pm weekdays) and weekend effects baked in so model comparison
is meaningful.

## Build order (get end-to-end working before polishing)

1. Train models on traffic_data.csv, pick the best (`ml/train_models.py`)
2. Build the graph + run Dijkstra on raw distance first, just to prove routing works
3. Swap in predicted travel time as edge weights
4. Add hospital selection loop
5. Wire into a Flask endpoint returning JSON
6. Plot the route as a plain line on a Leaflet map
7. Add "simulate traffic change" -> reroute check
8. Polish: Green Corridor highlight, styling, SQLite persistence of past emergencies

## Next step

Open this folder in VS Code with the Claude Code extension and ask it to
implement `ml/train_models.py` first, using `data/synthetic/traffic_data.csv`
with `travel_time_minutes` as the target and the other numeric columns as
features (one-hot encode `day`). Compare Linear Regression, Decision Tree,
and Random Forest on MAE/RMSE/R², and save the best model to
`ml/best_model.pkl`.
