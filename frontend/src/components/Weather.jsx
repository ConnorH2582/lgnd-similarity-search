import { useEffect, useState } from "react";

export default function Weather({ lat, lon }) {
  const [weather, setWeather] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/weather?lat=${lat}&lon=${lon}`
        );

        const data = await res.json();

        // Your backend definitely returns this field:
        const w = data.current_weather;

        if (!w) {
          console.warn("Weather: Missing current_weather:", data);
          setError(true);
          return;
        }

        setWeather(w);
      } catch (err) {
        console.error("Weather fetch failed:", err);
        setError(true);
      }
    };

    fetchWeather();
  }, [lat, lon]);

  if (error) {
    return <div>Weather unavailable</div>;
  }

  if (!weather) {
    return <div>Loading weather…</div>;
  }

  return (
    <div style={{ fontSize: "14px" }}>
      <strong>Weather</strong>
      <br />
      Temp: {weather.temperature}°C
      <br />
      Wind: {weather.windspeed} km/h
      <br />
      Direction: {weather.winddirection}°
    </div>
  );
}
