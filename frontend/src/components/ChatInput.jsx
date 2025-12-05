import { useState } from "react";

export default function ChatInput({ onSend }) {
  const [msg, setMsg] = useState("");

  const send = () => {
    if (!msg.trim()) return;
    onSend(msg);
    setMsg("");
  };

  return (
    <div style={{ display: "flex", marginBottom: "10px" }}>
      <input
        style={{
          flexGrow: 1,
          padding: "10px",
          borderRadius: "6px",
          border: "1px solid #ccc",
        }}
        placeholder="Search for marinas, airports, planes…"
        value={msg}
        onChange={(e) => setMsg(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && send()}
      />
      <button
        onClick={send}
        style={{
          marginLeft: "10px",
          padding: "10px 16px",
          borderRadius: "6px",
          border: "none",
          background: "#333",
          color: "white",
          cursor: "pointer",
        }}
      >
        Go
      </button>
    </div>
  );
}
