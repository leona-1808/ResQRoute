# 🚑 ResQRoute — AI-Based Dynamic Emergency Route & Green Corridor Optimization

**Live Demo:** [https://resqroute-g1wa.onrender.com/](https://resqroute-g1wa.onrender.com/)

> ⚠️ Hosted on Render's free tier — the app may take 30–50 seconds to wake up on first load if it's been idle. After that, it runs normally.

---

## 📌 What this project does

ResQRoute simulates how an AI-assisted ambulance dispatch system could work:

1. 🧠 **Predicts current travel time** for every road using a trained ML model
2. 🗺️ **Finds the fastest route** to each hospital using Dijkstra's algorithm on those predictions
3. 🏥 **Picks the optimal hospital** — not the *nearest* one, the *fastest to reach*
4. 🚦 **Simulates a Green Corridor** by flagging the roads along the chosen route
5. 🔁 **Dynamically reroutes** when traffic conditions change, but only when it actually improves the outcome

> **Note:** Street names shown on the map are real Kakinada locations, used only to make the demo visually realistic. Hospital names are entirely fictional ("(Prototype)") and do not represent real hospitals, capacities, or response times. All traffic and travel-time data is synthetically generated.

---

## 🖥️ Try it live

Open the [live demo](https://resqroute-g1wa.onrender.com/) and:

1. 📍 Pick an emergency location and click **Create Emergency**
2. 🚧 Click **Simulate Traffic Jam** on a road *not* on your route → notice it correctly says **no reroute needed**
3. 🔥 Click **Jam Current Route** → watch it reroute live, choosing a different hospital
4. 🌙 Try the dark/light mode toggle in the header

---

## 🏗️ System architecture

```
Traffic Dataset (synthetic)
        ↓
ML Model (Linear Regression / Decision Tree / Random Forest)
        ↓
Predicted Travel Time per Road
        ↓
NetworkX Graph + Dijkstra Routing
        ↓
Optimal Hospital Selection (lowest predicted time, not nearest)
        ↓
Green Corridor Flag (roads on the chosen route)
        ↓
Traffic Change? → Re-predict → Still optimal? → Reroute if not
        ↓
Flask API → Leaflet Map + SQLite History
```

---

## 🔑 Key design decisions

### 🗄️ Why SQLite, not MySQL?
No rubric required MySQL, and SQLAlchemy keeps the persistence layer database-agnostic — the prototype stays simple now, and could point at MySQL later with a one-line connection-string change. SQLite avoids the overhead of running a separate database server for a prototype this size.

### 🏥 Why "Optimal Hospital," not "Nearest Hospital"?
Geographically nearest ≠ fastest to reach. A hospital 5 km away on a clear road can be faster than one 3 km away through heavy traffic. The system compares *predicted travel time* to every hospital and picks the minimum — a deliberate, explainable design choice.

### 📉 Why did Linear Regression win over Random Forest?
The synthetic traffic data was generated from a mostly linear relationship (distance ÷ speed + signal delay). Linear Regression correctly matched that underlying structure, outperforming Random Forest and Decision Tree on MAE, RMSE, and R². This is a legitimate result — more complex models don't automatically win, and validating that with metrics is good practice, not a flaw.

| Model | MAE | RMSE | R² |
|---|---|---|---|
| **Linear Regression** | 0.696 | 0.852 | **0.729** |
| Random Forest | 0.709 | 0.882 | 0.709 |
| Decision Tree | 0.854 | 1.149 | 0.506 |

### 🚦 Why is Green Corridor just a flag?
Real traffic-signal control requires hardware integration and is out of scope for a prototype. The system identifies which roads *would* get signal priority and flags them (`NORMAL → PRIORITY → NORMAL`), without claiming to control real infrastructure.

---

## 🧩 Tech stack

| Layer | Tool |
|---|---|
| 🐍 Language | Python 3 |
| 📊 Data & ML | Pandas, NumPy, scikit-learn |
| 🗺️ Routing | NetworkX (Dijkstra) |
| 🌐 Backend | Flask, Flask-SQLAlchemy |
| 🗄️ Database | SQLite |
| 🖼️ Frontend | HTML, CSS, JavaScript, Leaflet.js |
| ☁️ Deployment | Render |
| 🔧 Version control | Git + GitHub |

---

## 📁 Project structure

```
ResQRoute/
├── data/synthetic/
│   ├── roads.csv                  # 3×3 synthetic road grid (nodes A–I)
│   ├── hospitals.csv              # 3 fictional hospitals
│   ├── generate_traffic_data.py   # regenerates traffic_data.csv
│   └── traffic_data.csv           # ML training data (252 rows)
│
├── ml/
│   ├── train_models.py            # trains & compares LR / DT / RF
│   └── best_model.pkl             # saved winning model
│
├── routing/
│   ├── graph_builder.py           # builds the NetworkX graph
│   ├── dijkstra_route.py          # routing on predicted travel time
│   ├── hospital_selector.py       # optimal hospital selection
│   └── dynamic_reroute.py         # traffic-change + reroute logic
│
├── backend/
│   ├── app.py                     # Flask API + SQLite setup
│   └── models/db_models.py        # SQLAlchemy Emergency model
│
├── frontend/
│   ├── templates/dashboard.html
│   └── static/
│       ├── map.js                 # Leaflet map + all interactivity
│       └── style.css              # light/dark theme, custom icons
│
├── Procfile                       # Render start command
├── requirements.txt
└── README.md
```

---

## 🧪 Running it locally

```bash
# clone the repo
git clone https://github.com/leona-1808/ResQRoute.git
cd ResQRoute

# set up a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# install dependencies
pip install -r requirements.txt

# (optional) regenerate the ML model
python ml/train_models.py

# run the app
python backend/app.py
```

Then open **http://127.0.0.1:5000** in your browser.

---

## 🔌 API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/emergency` | POST | Create an emergency, get optimal hospital + route |
| `/api/traffic/simulate` | POST | Simulate a traffic change (specific road or time shift) |
| `/api/traffic/jam-current-route` | POST | Jam every road on the active route (guaranteed reroute) |
| `/api/history` | GET | View all past emergencies (JSON) |

---

## 🚀 Possible future work

- 📊 Power BI dashboard connected to `/api/history`
- 🌦️ Weather as a model feature
- 🚑 Multiple ambulances / priority levels
- 🗺️ Real city road-network data
- 🚦 Real traffic-signal integration

---

*This is a student prototype built for demonstration purposes. All traffic, hospital, and performance data is synthetically generated.*
