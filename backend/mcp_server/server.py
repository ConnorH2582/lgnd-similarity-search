"""FastAPI MCP server for LGND take-home.

Exposes:
- /similarity/text
- /similarity/point

Includes startup logging.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .duckdb_client import DuckDBClient
from .handlers import Handlers
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


app = FastAPI(title="LGND MCP Server")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB + handlers
db = DuckDBClient()
handlers = Handlers(db)


@app.on_event("startup")
async def startup_event():
    """Log server startup."""
    logger.info("[Server] MCP server initialized and ready.")


# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------
@app.get("/similarity/text")
async def similarity_text(q: str = Query(..., description="Text query")):
    """Similarity search via text → OSM → spatial lookup → vector search.

    Args:
        q (str): Query text.

    Returns:
        List[Dict[str, Any]]: Similar chips.
    """
    return await handlers.similarity_by_text(q)


@app.get("/similarity/point")
async def similarity_point(
    lon: float = Query(..., description="Longitude"),
    lat: float = Query(..., description="Latitude"),
):
    """Similarity search via direct point location.

    Args:
        lon (float): Query longitude.
        lat (float): Query latitude.

    Returns:
        List[Dict[str, Any]]: Similar chips.
    """
    return await handlers.similarity_by_point(lon, lat)
