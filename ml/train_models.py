"""
ml/train_models.py

Trains Linear Regression, Decision Tree, and Random Forest to predict
travel_time_minutes from traffic conditions. Compares them on MAE, RMSE,
R², and saves the best one to ml/best_model.pkl.
"""

import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ---- Load data ----
df = pd.read_csv("data/synthetic/traffic_data.csv")

# ---- Feature engineering ----
# One-hot encode 'day' (Mon, Tue, ... Sun)
df = pd.get_dummies(df, columns=["day"], drop_first=True)

feature_cols = [
    "hour", "vehicle_count", "traffic_density", "avg_speed",
    "road_length_km", "signal_delay_min"
] + [c for c in df.columns if c.startswith("day_")]

X = df[feature_cols]
y = df["travel_time_minutes"]

# ---- Train/test split ----
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ---- Define models ----
models = {
    "Linear Regression": LinearRegression(),
    "Decision Tree": DecisionTreeRegressor(max_depth=6, random_state=42),
    "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42),
}

results = {}
best_model = None
best_model_name = None
best_r2 = -np.inf

for name, model in models.items():
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)

    results[name] = {"MAE": mae, "RMSE": rmse, "R2": r2}

    print(f"\n{name}")
    print(f"  MAE:  {mae:.3f} minutes")
    print(f"  RMSE: {rmse:.3f} minutes")
    print(f"  R2:   {r2:.3f}")

    if r2 > best_r2:
        best_r2 = r2
        best_model = model
        best_model_name = name

print(f"\n==> Best model: {best_model_name} (R2 = {best_r2:.3f})")

# ---- Save best model + feature columns (needed later for prediction) ----
joblib.dump({"model": best_model, "features": feature_cols}, "ml/best_model.pkl")
print("Saved to ml/best_model.pkl")