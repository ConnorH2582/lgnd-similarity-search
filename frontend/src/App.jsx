import { useState } from "react";
import axios from "axios";
import "./App.css";

/**
 * LGND Similarity Search Frontend
 *
 * - Matches original UI/UX (alignment, disabled button, grid layout)
 * - Adds lightweight frontend logging
 * - Safely handles backend response shape
 * - Prevents .map errors
 */
export default function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);   // matches original shape
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e) {
    if (e?.preventDefault) e.preventDefault();
    if (!query.trim()) return;

    console.log("[Frontend] Searching for:", query);

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await axios.get("http://127.0.0.1:8000/similarity/text", {
        params: { q: query },
      });

      console.log("[Frontend] Raw backend response:", res.data);

      // SAFETY: ensure results array always exists
      const safe = {
        ...res.data,
        results: Array.isArray(res.data.results) ? res.data.results : [],
      };

      setResult(safe);
      console.log("[Frontend] Parsed results:", safe);
    } catch (err) {
      console.error("[Frontend] Search error:", err);
      setError("Something went wrong contacting the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <h1>LGND SF Imagery Search</h1>

      {/* Original layout restored */}
      <form onSubmit={handleSearch} style={{ marginBottom: 16 }}>
        <input
          style={{ width: "70%", padding: 8, marginRight: 8 }}
          placeholder='Try "coastal marina" or "airport"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Render results in original grid */}
      {result && result.results && (
        <div>
          <h2>Results</h2>

          {result.poi && (
            <p>
              OSM anchor: <strong>{result.poi.name}</strong>
            </p>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, 150px)",
              gap: 12,
            }}
          >
            {result.results.map((chip) => (
              <div key={chip.chips_id} style={{ fontSize: 12 }}>
                <img
                  src={`https://lgnd-fullstack-takehome-thumbnails.s3.us-east-2.amazonaws.com/${chip.chips_id}_256.jpeg`}
                  alt={chip.chips_id}
                  style={{
                    width: "100%",
                    height: 100,
                    objectFit: "cover",
                    borderRadius: 4,
                  }}
                  onLoad={() =>
                    console.log(`[Frontend] Loaded thumbnail for ${chip.chips_id}`)
                  }
                  onError={() =>
                    console.error(
                      `[Frontend] Failed to load thumbnail for ${chip.chips_id}`
                    )
                  }
                />

                <div>sim: {chip.similarity.toFixed(3)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
