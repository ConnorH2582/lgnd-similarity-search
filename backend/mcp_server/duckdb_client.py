"""DuckDB client for vector and spatial operations over LGND embeddings.

Handles:
- Spatial lookup: find chip whose geometry contains a lon/lat point
- Vector similarity search: cosine similarity against 1024-dim embedding vectors
- Metadata lookup: chip centroid for display

Includes lightweight performance logging.
"""

from typing import List, Dict, Any, Optional
import duckdb
import numpy as np
import logging
import time
import os

logger = logging.getLogger(__name__)


class DuckDBClient:
    """Client for interacting with the `embeddings` DuckDB database."""

    def __init__(self, db_path: str = None) -> None:
        """Initialize DuckDB client and load spatial extension.

        Args:
            db_path (str, optional): Optional path to the DuckDB file.
                If None, resolves the root-level embeddings.db automatically.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        if db_path is None:
            db_path = os.path.join(project_root, "embeddings.db")

        self.db_path = db_path
        logger.info(f"[DuckDBClient] Connecting to DuckDB at {db_path}")

        # Connect to DuckDB
        self.con = duckdb.connect(db_path)

        # Validate table existence
        tables = self.con.execute("SHOW TABLES").fetchall()
        logger.info(f"[DuckDBClient] Database tables: {tables}")

        if ('embeddings',) not in tables:
            logger.error(
                "[DuckDBClient] ERROR: Database is missing 'embeddings' table. "
                f"DB path: {db_path}"
            )

        self._load_extensions()

    def _load_extensions(self) -> None:
        """Install and load DuckDB spatial extension."""
        try:
            logger.info("[DuckDBClient] Installing spatial extension…")
            self.con.execute("INSTALL spatial;")
        except Exception:
            logger.info("[DuckDBClient] Spatial extension already installed.")

        self.con.execute("LOAD spatial;")
        logger.info("[DuckDBClient] Spatial extension loaded successfully.")

    # ----------------------------------------------------------------------
    # Spatial Lookup
    # ----------------------------------------------------------------------
    def get_chip_by_point(self, lon: float, lat: float) -> Optional[Dict[str, Any]]:
        """Return chip metadata for the tile containing (lon, lat).

        Args:
            lon (float): Longitude.
            lat (float): Latitude.

        Returns:
            Optional[Dict[str, Any]]: Dict containing:
                - chips_id (str)
                - vec (List[float]): 1024-dim embedding vector
            Returns None if no geometry contains the point.
        """
        logger.info(f"[DuckDBClient] Spatial query at lon={lon}, lat={lat}")
        t0 = time.perf_counter()

        query = """
            SELECT chips_id, vec
            FROM embeddings
            WHERE ST_Contains(geom, ST_Point(?, ?))
            LIMIT 1;
        """

        row = self.con.execute(query, [lon, lat]).fetchone()
        dt = time.perf_counter() - t0

        if not row:
            logger.warning(
                f"[DuckDBClient] No chip found for point ({lon}, {lat}) "
                f"(elapsed={dt:.3f}s)"
            )
            return None

        chips_id, vec = row
        logger.info(
            f"[DuckDBClient] Spatial lookup matched chip={chips_id} "
            f"(elapsed={dt:.3f}s)"
        )

        return {"chips_id": chips_id, "vec": vec}

    # ----------------------------------------------------------------------
    # Similarity Search
    # ----------------------------------------------------------------------
    def get_similar_chips(
        self, seed_vec: List[float], limit: int = 12
    ) -> List[Dict[str, Any]]:
        """Run cosine similarity search against embedding vectors.

        Args:
            seed_vec (List[float]): Normalized 1024-dim vector.
            limit (int): Number of results to return.

        Returns:
            List[Dict[str, Any]]: Chips sorted by similarity descending.
        """
        logger.info(f"[DuckDBClient] Starting similarity search (top={limit})")
        t0 = time.perf_counter()

        seed_vec = np.array(seed_vec, dtype=np.float32)
        if seed_vec.shape[0] != 1024:
            raise ValueError(
                f"Expected seed_vec of length 1024, got {seed_vec.shape[0]}"
            )

        norm = np.linalg.norm(seed_vec)
        if norm == 0:
            raise ValueError("Seed embedding vector has zero magnitude.")

        seed_vec = (seed_vec / norm).tolist()

        query = f"""
            SELECT
                chips_id,
                array_cosine_similarity(vec, CAST(? AS FLOAT[1024])) AS similarity,
                ST_X(ST_Centroid(geom)) AS lon,
                ST_Y(ST_Centroid(geom)) AS lat
            FROM embeddings
            ORDER BY similarity DESC
            LIMIT {limit};
        """

        rows = self.con.execute(query, [seed_vec]).fetchall()
        dt = time.perf_counter() - t0

        logger.info(
            f"[DuckDBClient] Similarity search returned {len(rows)} results "
            f"(elapsed={dt:.3f}s)"
        )

        results: List[Dict[str, Any]] = []
        for chips_id, sim, lon, lat in rows:
            results.append(
                {
                    "chips_id": chips_id,
                    "similarity": float(sim),
                    "lon": float(lon),
                    "lat": float(lat),
                }
            )

        return results

    # ----------------------------------------------------------------------
    # Metadata
    # ----------------------------------------------------------------------
    def get_chip_metadata(self, chips_id: str) -> Optional[Dict[str, Any]]:
        """Fetch centroid metadata for a specific chip.

        Args:
            chips_id (str): Chip identifier.

        Returns:
            Optional[Dict[str, Any]]: Dict with chip metadata, or None.
        """
        query = """
            SELECT chips_id,
                   ST_X(ST_Centroid(geom)) AS lon,
                   ST_Y(ST_Centroid(geom)) AS lat
            FROM embeddings
            WHERE chips_id = ?
            LIMIT 1;
        """

        row = self.con.execute(query, [chips_id]).fetchone()
        if not row:
            logger.warning(f"[DuckDBClient] Metadata not found for chip={chips_id}")
            return None

        chips_id, lon, lat = row
        return {"chips_id": chips_id, "lon": lon, "lat": lat}
