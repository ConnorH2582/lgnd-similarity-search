"""FastAPI application exposing similarity search endpoints."""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .handlers import MCPHandlers

app = FastAPI(
    title="LGND Similarity Search Server",
    description="MVP backend for similarity search over SF imagery using DuckDB and OSM.",
)

# Instantiate application handlers once at startup.
handlers = MCPHandlers(db_path="./embeddings.db")

# Allow the Vite dev server (React frontend) to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Return a simple health check response.

    Returns:
        A dictionary indicating that the server is healthy.
    """
    return {"ok": True}


@app.get("/similarity/text")
async def similarity_text(
    q: str = Query(..., description="Natural-language query, e.g. 'coastal marina'."),
) -> dict:
    """Run a similarity search based on a text query.

    Args:
        q: Natural-language query describing the target area or feature.

    Returns:
        A JSON-serializable dictionary containing similarity search results.
    """
    return await handlers.similarity_by_text(q)


@app.get("/similarity/point")
async def similarity_point(
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
    return await handlers.similarity_by_point(lon, lat)
