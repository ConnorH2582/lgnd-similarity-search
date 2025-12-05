# LGND Similarity Search – Full-Stack Demo Application

A full-stack geospatial similarity search application built for the LGND AI take-home assessment.

Users can enter natural-language queries (e.g., **“marina”**, **“airport”**, **“parking lot”**), which are resolved to real geographic coordinates using OpenStreetMap (OSM).  
The backend then finds the imagery chip covering that location inside a DuckDB database and runs vector similarity search to return visually similar chips.  
The frontend displays results on an interactive map with thumbnails and live weather at each location.

---

# 🧩 System Components

- **FastAPI backend**
- **DuckDB embeddings database**
- **Real OSM geocoding (cached + warm)**
- **Vector similarity search**
- **React + Leaflet frontend**
- **Live weather (Open-Meteo API)**
- **Application warmup + caching for fast demo responsiveness**

---

# 📁 Project Structure

```
lgnd-similarity-search/
├── backend/
│   ├── mcp_server/
│   │   ├── server.py            # FastAPI entrypoint
│   │   ├── handlers.py          # Geocode → chip → similarity orchestration
│   │   ├── duckdb_client.py     # DuckDB abstraction layer
│   │   ├── osm_client.py        # OSM (sync + async) with caching
│   ├── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── SearchInput.jsx
│   │   │   ├── Weather.jsx
│   │   ├── index.css
│   │   ├── app.css
│   ├── package.json
│
├── embeddings.db                 # Required LGND-provided DuckDB database
└── README.md
```

---

# 📦 Required Dataset: `embeddings.db`

LGND provides the DuckDB file `embeddings.db`, which contains:

- Embedding vectors (1024-dim, float32)
- Spatial geometry
- Chip IDs
- Metadata used for similarity search

### Download it from the LGND assignment source and place it here:

```
lgnd-similarity-search/backend/embeddings.db
```

Verify it exists:

```bash
ls
# or
dir
```

If `embeddings.db` is missing, the backend will not run.

---

# 📝 Assumptions & Clarifications

- The only required dataset is **embeddings.db**.
- OSM Nominatim is used for text → geocode lookups.
- All OSM results are cached for speed.
- DuckDB performs spatial + cosine similarity search.
- Weather data is retrieved via **Open-Meteo** (no API key required).
- Multiple caching layers keep the demo responsive.
- UI is intentionally simple; focus is correctness + architecture.

---

# 🚀 Installation & Setup

Follow these steps to run the project locally.

---

## 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/lgnd-similarity-search.git
cd lgnd-similarity-search
```

---

## 2. Backend Setup (FastAPI + Python)

```bash
cd backend
```

### Create + activate a virtual environment

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Ensure `embeddings.db` is present

```bash
ls
```

### Run the backend

```bash
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Backend available at:

➡️ **http://localhost:8000**

---

## 3. Frontend Setup (React + Vite)

Open a new terminal window (leave backend running):

```bash
cd frontend
npm install
npm run dev
```

Frontend available at:

➡️ **http://localhost:5173**

---

# 🔌 Useful API Endpoints

### Similarity search by text (“marina”, “airport”, etc.)

```
GET http://localhost:8000/similarity/text?q=marina
```

### Similarity search by coordinate

```
GET http://localhost:8000/similarity/point?lon=-122.48&lat=37.80
```

### Weather lookup

```
GET http://localhost:8000/weather?lat=37.80&lon=122.48
```

### Health check

```
GET http://localhost:8000/health
```

---

# 🏗️ Architecture Overview

### High-level flow:

1. User enters a text query.
2. Frontend calls `/similarity/text?q=...`
3. Backend:
   - Geocodes text via OSM (cached)
   - Finds the chip polygon containing the coordinate
   - Fetches its embedding
   - Runs cosine similarity using DuckDB’s HNSW index
   - Returns top-N similar chips
4. Frontend:
   - Shows results in sidebar
   - Plots markers on a Leaflet map
   - Displays thumbnails + similarity scores
   - Fetches weather for each chip

### Caching layers:

- Text query → geocode  
- (lon, lat) → chip  
- chip_id → similarity results  

Startup includes a short warming phase for smoother demo performance.

---

# 🧑‍💻 Developer Notes

- Backend: **Python + FastAPI**
- Database: **DuckDB**
- Frontend: **React + Vite + React-Leaflet**
- Leaflet icons are configured specifically for Vite bundling.

---

# 🌿 Git Workflow (Example)

```bash
git checkout -b feature/similarity-caching
git add .
git commit -m "Implement caching and map/weather integration"
git push -u origin feature/similarity-caching

git checkout main
git pull
git merge feature/similarity-caching
git push
```

---

# 🎥 Demo Video

➡️ **[Watch the 3-minute demo](./demo/demo.mp4)**

---

# 🚀 Future Improvements

- Dockerize backend + frontend
- Add cluster-based map visualizations and basemap layers
- Use an external vector DB (FAISS, Milvus, PGVector)
- Add automated tests (unit + integration)
- Expand UI (filters, history, chip detail view, etc.)

