import { useState } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await axios.get("http://localhost:8000/similarity/text", {
        params: { q: query },
      });
      setResult(res.data);
    } catch (err) {
      console.error(err);
      setError("Something went wrong contacting the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <h1>LGND SF Imagery Search</h1>
      <form onSubmit={handleSearch} style={{ marginBottom: 16 }}>
        <input
          style={{ width: "70%", padding: 8, marginRight: 8 }}
          placeholder='Try "coastal marina" or "airport"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && result.results && (
        <div>
          <h2>Results</h2>
          {result.poi && (
            <p>
              OSM anchor: <strong>{result.poi.name}</strong>
            </p>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, 150px)", gap: 12 }}>
            {result.results.map((r) => (
              <div key={r.chips_id} style={{ fontSize: 12 }}>
                <img
                  src={r.thumbnail}
                  alt={r.chips_id}
                  style={{ width: "100%", height: 100, objectFit: "cover" }}
                />
                <div>sim: {r.similarity.toFixed(3)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
