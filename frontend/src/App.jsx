import { useState } from "react";
import "./App.css";

/**
 * App component for LGND similarity search demo.
 *
 * Provides:
 * - Search bar for text queries (e.g. "airport", "marina")
 * - Calls MCP backend for similarity search
 * - Renders thumbnail results
 * - Lightweight console logging for debugging/demo purposes
 */
export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /**
   * Perform text-based similarity search via MCP backend.
   */
  const handleSearch = async () => {
    if (!query.trim()) return;

    console.log("[Frontend] Searching for:", query);
    setLoading(true);
    setError("");
    setResults([]);

    try {
      const resp = await fetch(
        `http://127.0.0.1:8000/similarity/text?q=${encodeURIComponent(query)}`
      );

      if (!resp.ok) {
        throw new Error(`Server responded with ${resp.status}`);
      }

      const data = await resp.json();
      console.log("[Frontend] Results received:", data);

      setResults(data);
    } catch (err) {
      console.error("[Frontend] Search error:", err);
      setError("Error during search. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  /**
   * Render a single result card, including thumbnail image.
   */
  const renderResult = (chip) => {
    const thumbURL = `https://lgnd-fullstack-takehome-thumbnails.s3.us-east-2.amazonaws.com/${chip.chips_id}_256.jpeg`;

    return (
      <div key={chip.chips_id} className="result-card">
        <img
          src={thumbURL}
          alt="chip thumbnail"
          className="result-image"
          onLoad={() =>
            console.log(`[Frontend] Thumbnail loaded for ${chip.chips_id}`)
          }
          onError={() =>
            console.error(`[Frontend] Failed to load thumbnail: ${thumbURL}`)
          }
        />

        <div className="result-meta">
          <p><strong>Chip ID:</strong> {chip.chips_id}</p>
          <p><strong>Similarity:</strong> {chip.similarity.toFixed(4)}</p>
          <p>
            <strong>Location:</strong> {chip.lat.toFixed(4)},{" "}
            {chip.lon.toFixed(4)}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      <h1>LGND Similarity Search</h1>

      <div className="search-container">
        <input
          type="text"
          placeholder="Search for 'airport', 'marina', etc."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button onClick={handleSearch}>Search</button>
      </div>

      {loading && <p className="loading">Loading...</p>}
      {error && <p className="error">{error}</p>}

      <div className="results-grid">
        {results.map((chip) => renderResult(chip))}
      </div>
    </div>
  );
}
