import { useEffect, useState } from "react";
import { api } from "../api.js";

function describe(event) {
  const d = event.details || {};
  if (event.action === "toggled") return d.enabled ? "Turned on" : "Turned off";
  if (event.action === "created") return `Created at ${d.rollout_percentage ?? 0}% rollout`;
  if (event.action === "deleted") return "Deleted";
  if (event.action === "updated") {
    return Object.entries(d.changes || {})
      .map(([field, change]) =>
        field === "rollout_percentage"
          ? `rollout ${change.from}% → ${change.to}%`
          : `${field.replace("_", " ")} changed`,
      )
      .join(", ");
  }
  return event.action;
}

export default function AuditLog({ flagKey, version }) {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    api.audit(flagKey, 15).then(setEvents).catch(() => setEvents([]));
  }, [flagKey, version]);

  return (
    <div className="card">
      <h2>History</h2>
      {events.length === 0 ? (
        <p className="muted small">No changes recorded.</p>
      ) : (
        <ol className="timeline">
          {events.map((event) => (
            <li key={event.id}>
              <span className={`dot ${event.action}`} />
              <div>
                <div>{describe(event)}</div>
                <div className="muted small">{new Date(event.created_at).toLocaleString()}</div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
