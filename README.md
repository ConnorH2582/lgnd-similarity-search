LGND Similarity Search – Full-Stack Demo Application

A full-stack geospatial similarity search application built for the LGND AI take-home assessment.

Users can enter natural-language queries (for example: “marina”, “airport”, “parking lot”), which are resolved to real geographic coordinates using OpenStreetMap (OSM). The backend then finds the imagery chip covering that location in a DuckDB database and runs vector similarity search to return visually similar chips. The frontend displays results on an interactive map with thumbnails and live weather at each result location.

The system consists of:

FastAPI backend

DuckDB embeddings database

Real OSM geocoding (cached + warm)

Vector similarity search

React + Leaflet frontend

Live weather integration (Open-Meteo API)

Caching and warmup for fast demo performance

# 📁 Project Structure

lgnd-similarity-search/

├── backend/
│ ├── mcp_server/
│ │ ├── server.py # FastAPI application entrypoint
│ │ ├── handlers.py # Orchestrates geocode → chip lookup → similarity
│ │ ├── duckdb_client.py # DuckDB abstraction layer
│ │ ├── osm_client.py # OSM geocoder (async + sync warmup)
│ ├── requirements.txt
│
├── frontend/
│ ├── src/
│ │ ├── App.jsx
│ │ ├── components/
│ │ │ ├── ChatInput.jsx
│ │ │ ├── Weather.jsx
│ │ ├── index.css
│ │ ├── app.css
│ ├── package.json
│
├── embeddings.db # LGND-provided DuckDB embeddings database (required)
└── README.md

Required Dataset: embeddings.db

LGND provides a DuckDB file named embeddings.db as part of the take-home assignment.
It contains the imagery chip metadata and embedding vectors used for similarity search.

If you do not already have it:

Download embeddings.db from the original LGND assignment source (Drive link, ZIP, or GitHub asset).

Place it into the backend folder:

lgnd-similarity-search/backend/embeddings.db

From the backend directory, you should be able to run:

ls or dir 
and see embeddings.db listed.

The backend will not work without this file.

Assumptions & Clarifications

The only required dataset is embeddings.db provided by LGND.

OSM Nominatim is used for real geocoding. Results are cached so repeated queries do not repeatedly hit the external API.

Similarity search uses cosine similarity over the embedding vectors stored in embeddings.db.

Weather data comes from Open-Meteo, which does not require an API key.

Caching is used at multiple layers (geocode, chip lookup, similarity results) to keep the demo responsive while preserving correctness.

The UI is intentionally simple; the focus is architecture, correctness, and a clear UX.

Installation & Setup

These are the steps a new developer should follow to run the app locally.

1. Clone the repository

From your terminal:

git clone https://github.com/
<your-username>/lgnd-similarity-search.git

cd lgnd-similarity-search

2. Backend Setup (Python + FastAPI)

From the project root:

cd backend

Create and activate a virtual environment:

python3 -m venv venv

On macOS / Linux:
source venv/bin/activate

On Windows:
venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Confirm embeddings.db is present in this folder:

ls

You should see embeddings.db in the listing. If not, copy it here as described above.

Run the backend:

uvicorn server:app --reload --host 127.0.0.1 --port 8000

The backend will be available at:

http://localhost:8000

3. Frontend Setup (React + Vite)

Open a new terminal window (keep the backend running):

From the project root:

cd frontend

Install frontend dependencies:

npm install

Start the dev server:

npm run dev

The frontend will be available at:

http://localhost:5173

Useful API Endpoints

These are helpful for manual testing in a browser or with curl/Postman:

Similarity by text (for example, “marina”):

GET http://localhost:8000/similarity/text?q=marina

Similarity by point:

GET http://localhost:8000/similarity/point?lon=-122.48&lat=37.80

Weather at a coordinate:

GET http://localhost:8000/weather?lat=37.80&lon=-122.48

Health check:

GET http://localhost:8000/health

Architecture Overview (Conceptual)

High-level flow:

User enters a text query (for example, “marina”) in the frontend.

The React frontend calls the backend at /similarity/text?q=....

The FastAPI backend:

Uses OSM to geocode text into latitude/longitude (with caching).

Finds the imagery chip whose polygon contains that point via DuckDB.

Retrieves the chip’s embedding vector.

Runs cosine similarity against all other chips in embeddings.db.

Returns the top-N similar chips with coordinates and thumbnail URLs.

The frontend:

Lists results in a sidebar.

Plots markers on a Leaflet map.

Shows thumbnails and similarity scores in a popup.

Calls /weather?lat=...&lon=... and shows weather in the popup.

Caching layers:

Text query → geocode result (OSM)

(lon, lat) → chip

seed chip id → list of similar chips

Warmup runs once at startup for a few common queries so the first demo interactions are already “warm”.

Developer Notes

Backend is Python 3 + FastAPI.

Database access is via DuckDB (no external DB server required).

Frontend is React + Vite + React-Leaflet.

Leaflet markers are explicitly configured so default icons work correctly with Vite bundling.

Git / Commit Workflow (Example)

Typical workflow for iterating on this project:

Create a feature branch:

git checkout -b feature/similarity-caching

Stage and commit your changes:

git add .

git commit -m "Implement caching, warmup, and UI map/weather integration"

Push to GitHub:

git push -u origin feature/similarity-caching

Merge into main after review:

git checkout main

git pull

git merge feature/similarity-caching

git push

Future Improvements

Some natural extension points:

Dockerize backend and frontend for single-command startup.

Add clustering and additional basemap options (satellite, dark mode).

Use an external vector database (FAISS, Milvus, PGVector) if scaling beyond the current dataset.

Add automated tests (unit + integration) for OSM client, DuckDB client, and handlers.

Add richer UI elements (filters, query history, chip detail views, etc.).