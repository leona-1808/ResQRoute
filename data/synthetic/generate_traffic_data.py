"""
generate_traffic_data.py

Generates a synthetic traffic dataset for training the travel-time
prediction model (Linear Regression / Decision Tree / Random Forest).

Each row = one observation of a road at a particular hour of a particular
day, with traffic conditions and the resulting (synthetically simulated)
travel time.

Run:
    python generate_traffic_data.py
Output:
    traffic_data.csv (same folder)
"""

import numpy as np
import pandas as pd

np.random.seed(42)

# ---- Load road base distances so travel time scales realistically ----
roads = pd.read_csv("roads.csv")

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS = list(range(24))
OBS_PER_ROAD_PER_DAY = 3  # random hours sampled per road per day

rows = []

for _, road in roads.iterrows():
    road_id = road["road_id"]
    base_distance = road["base_distance_km"]

    for day in DAYS:
        # sample a few random hours per day for this road
        sampled_hours = np.random.choice(HOURS, size=OBS_PER_ROAD_PER_DAY, replace=False)

        for hour in sampled_hours:
            # --- simulate rush-hour effect ---
            is_rush = hour in [8, 9, 10, 17, 18, 19]
            is_weekend = day in ["Sat", "Sun"]

            # base vehicle count, higher during rush hour, lower on weekends
            base_vehicle_count = np.random.randint(20, 80)
            if is_rush and not is_weekend:
                vehicle_count = base_vehicle_count + np.random.randint(40, 100)
            elif is_weekend:
                vehicle_count = max(5, base_vehicle_count - np.random.randint(10, 30))
            else:
                vehicle_count = base_vehicle_count

            # traffic density derived from vehicle count (0-1 scale, with noise)
            traffic_density = np.clip(vehicle_count / 180 + np.random.normal(0, 0.05), 0.05, 1.0)

            # average speed drops as density increases
            max_speed = 60  # km/h free-flow speed
            avg_speed = np.clip(max_speed * (1 - 0.75 * traffic_density) + np.random.normal(0, 3), 8, max_speed)

            # signal delay (minutes) — more delay when density is high
            signal_delay = np.clip(np.random.normal(1 + 3 * traffic_density, 0.5), 0.2, 6)

            # --- travel time formula (ground truth generator) ---
            # time = distance/speed (hours -> minutes) + signal delay + noise
            drive_time_min = (base_distance / avg_speed) * 60
            travel_time = drive_time_min + signal_delay + np.random.normal(0, 0.8)
            travel_time = max(travel_time, 1.5)

            rows.append({
                "road_id": road_id,
                "day": day,
                "hour": hour,
                "vehicle_count": int(vehicle_count),
                "traffic_density": round(traffic_density, 3),
                "avg_speed": round(avg_speed, 2),
                "road_length_km": base_distance,
                "signal_delay_min": round(signal_delay, 2),
                "travel_time_minutes": round(travel_time, 2),
            })

df = pd.DataFrame(rows)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle
df.to_csv("traffic_data.csv", index=False)

print(f"Generated {len(df)} rows -> traffic_data.csv")
print(df.head())
