"""FastAPI application exposing similarity search endpoints."""

import logging
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .handlers import MCPHandlers

logger = logging.getLogger(__name__)


app = FastAPI(
    title="LGND Similarity Search Server",
    description="MVP backend for similarity search over SF imagery using DuckDB and OSM.",
)

# Instantiate application handlers once at startup.
handlers = MCPHandlers(db_path="./embeddings.db")


# ----------------------------------------------------------------------
# CORS (unchanged)
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    """Return a simple health check response.

    Returns:
        A dictionary indicating that the server is healthy.
    """
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
    """Run a similarity search based on a text query.

    Args:
        q: Natural-language query describing the target area or feature.

    Returns:
        A JSON-serializable dictionary containing similarity search results.
    """
    logger.info(f"[Server] /similarity/text → query='{q}'")
    return await handlers.similarity_by_text(q)


@app.get("/similarity/point")
async def similarity_point(
    request: Request,
    lon: float = Query(..., description="Longitude in WGS84."),
    lat: float = Query(..., description="Latitude in WGS84."),
) -> dict:
    """Run a similarity search anchored at a longitude/latitude point.

    Args:
        lon: Longitude in WGS84.
        lat: Latitude in WGS84.

    Returns:
        A JSON-serializable dictionary containing similarity search results.
    """
    logger.info(f"[Server] /similarity/point → lon={lon}, lat={lat}")
    return await handlers.similarity_by_point(lon, lat)
