"""FastAPI application exposing similarity search endpoints."""

import logging
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx   # NEW: for weather API

from .handlers import MCPHandlers

logger = logging.getLogger(__name__)


app = FastAPI(
    title="LGND Similarity Search Server",
    description="MVP backend for similarity search over SF imagery using DuckDB and OSM.",
)

# Instantiate application handlers once at startup.
handlers = MCPHandlers(db_path="./embeddings.db")


# ----------------------------------------------------------------------
# CORS — FIXED: allow_credentials must be False when allow_origins=["*"]
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # all origins allowed for demo
    allow_credentials=False,    # MUST be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------
# Startup Event
# ----------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("[Server] LGND Similarity Search Server is starting up...")
    logger.info("[Server] Handlers + DuckDB client initialized successfully.")


# ----------------------------------------------------------------------
# Health Endpoint
# ----------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    """Return a simple health check response."""
    logger.debug("[Server] Health check requested.")
    return {"ok": True}


# ----------------------------------------------------------------------
# Similarity Endpoints
# ----------------------------------------------------------------------
@app.get("/similarity/text")
async def similarity_text(
    request: Request,
    q: str = Query(..., description="Natural-language query, e.g. 'coastal marina'."),
) -> dict:
    """Run a similarity search based on a text query."""
    logger.info(f"[Server] /similarity/text → query='{q}'")
    return await handlers.similarity_by_text(q)


@app.get("/similarity/point")
async def similarity_point(
    request: Request,
    lon: float = Query(..., description="Longitude in WGS84."),
    lat: float = Query(..., description="Latitude in WGS84."),
) -> dict:
    """Run a similarity search anchored at a longitude/latitude point."""
    logger.info(f"[Server] /similarity/point → lon={lon}, lat={lat}")
    return await handlers.similarity_by_point(lon, lat)


# ----------------------------------------------------------------------
# WEATHER ENDPOINT 🌤️
# ----------------------------------------------------------------------
@app.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude in WGS84."),
    lon: float = Query(..., description="Longitude in WGS84."),
) -> dict:
    """
    Fetch current weather for the given coordinates using Open-Meteo API.
    """
    logger.info(f"[Server] /weather → lat={lat}, lon={lon}")

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        logger.error(f"[Weather] API error: {response.text}")
        return {"error": "Weather service unavailable"}

    return response.json()
