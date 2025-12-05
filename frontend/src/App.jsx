import { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import SearchInput from "./components/SearchInput";
import Weather from "./components/Weather";

// -----------------------------------------------------------
// 🔥 LEAFLET MARKER ICON FIX (Vite + React-Leaflet)
// -----------------------------------------------------------
import L from "leaflet";
import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

// Explicitly define the default marker icon
const DefaultIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Apply globally
L.Marker.prototype.options.icon = DefaultIcon;

// -----------------------------------------------------------
// MAIN APP COMPONENT
// -----------------------------------------------------------
export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  // NEW: Search function now takes the query directly (fixes first-click bug)
  const search = async (inputQuery) => {
    const q = inputQuery ?? query;
    if (!q.trim()) return;

    // Clear existing results (forces re-render)
    setResults([]);

    const res = await fetch(
      `http://localhost:8000/similarity/text?q=${encodeURIComponent(q)}`
    );
    const data = await res.json();

    // Ensure fresh identity for React
    setResults([...data.results]);
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* LEFT SIDEBAR */}
      <div
        style={{
          width: "350px",
          padding: "20px",
          background: "#fafafa",
          borderRight: "1px solid #ddd",
          display: "flex",
          flexDirection: "column",
          zIndex: 10,
        }}
      >
        <h2>Image Search</h2>

        <SearchInput
          onSend={(msg) => {
            setQuery(msg);
            search(msg);   // 🔥 call search directly with the message
          }}
        />

        <h3 style={{ marginTop: "20px" }}>Results ({results.length})</h3>

        <div
          style={{
            overflowY: "auto",
            flexGrow: 1,
            border: "1px solid #eee",
            borderRadius: "6px",
            padding: "10px",
            background: "white",
          }}
        >
          {results.length === 0 && <p>No results yet.</p>}

          {results.map((r) => (
            <div
              key={r.chips_id}
              style={{
                marginBottom: "14px",
                padding: "10px",
                border: "1px solid #ddd",
                borderRadius: "6px",
                background: "white",
              }}
            >
              <strong>{r.chips_id}</strong>
              <br />
              <small>
                similarity: {r.similarity}
                <br />
                lat: {r.lat}, lon: {r.lon}
              </small>

              {r.thumbnail && (
                <img
                  src={r.thumbnail}
                  onError={(e) => (e.currentTarget.src = "/fallback.jpg")}
                  alt="thumb"
                  style={{
                    width: "100%",
                    borderRadius: "6px",
                    marginTop: "8px",
                    border: "1px solid #ccc",
                  }}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* MAP AREA */}
      <div style={{ flexGrow: 1, zIndex: 1 }}>
        <MapContainer
          center={[37.7749, -122.4194]}
          zoom={10}
          style={{
            height: "100%",
            width: "100%",
            zIndex: 1,
          }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* SAFE MARKER RENDERING */}
          {results
            .filter(
              (r) =>
                typeof r.lat === "number" &&
                typeof r.lon === "number" &&
                !isNaN(r.lat) &&
                !isNaN(r.lon)
            )
            .map((r) => (
              <Marker key={r.chips_id} position={[r.lat, r.lon]}>
                <Popup>
                  <strong>{r.chips_id}</strong>
                  <br />
                  similarity: {r.similarity}
                  <br />
                  <br />

                  {r.thumbnail && (
                    <img
                      src={r.thumbnail}
                      onError={(e) => (e.currentTarget.src = "/fallback.jpg")}
                      alt="thumb"
                      style={{
                        width: "150px",
                        borderRadius: "4px",
                        border: "1px solid #ccc",
                      }}
                    />
                  )}

                  <br />
                  <br />
                  <Weather lat={r.lat} lon={r.lon} />
                </Popup>
              </Marker>
            ))}
        </MapContainer>
      </div>
    </div>
  );
}
