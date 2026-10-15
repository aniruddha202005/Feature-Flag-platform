import { useState } from "react";
import { api } from "../api.js";

const REASONS = {
  FLAG_DISABLED: "Kill switch is off",
  TARGETED_USER: "User is on the always-on list",
  RULE_MATCH: "Matched a targeting rule",
  ROLLOUT_INCLUDED: "Bucket is inside the rollout",
  ROLLOUT_EXCLUDED: "Bucket is outside the rollout",
};

const parseAttributes = (text) =>
  Object.fromEntries(
    text
      .split("\n")
      .map((line) => line.split("="))
      .filter(([k, v]) => k?.trim() && v !== undefined)
      .map(([k, ...rest]) => [k.trim(), rest.join("=").trim()]),
  );

export default function EvaluatePanel({ flag }) {
  const [userId, setUserId] = useState("user_42");
  const [attrs, setAttrs] = useState("country=IN");
  const [result, setResult] = useState(null);
  const [latency, setLatency] = useState(null);
  const [error, setError] = useState("");

  const run = async (e) => {
    e.preventDefault();
    setError("");
    const start = performance.now();
    try {
      const res = await api.evaluate(flag.key, userId.trim(), parseAttributes(attrs));
      setLatency(performance.now() - start);
      setResult(res);
    } catch (err) {
      setError(err.message);
      setResult(null);
    }
  };

  return (
    <div className="card">
      <h2>Test evaluation</h2>
      <form onSubmit={run}>
        <label className="field">
          <span>User ID</span>
          <input className="input mono" value={userId} onChange={(e) => setUserId(e.target.value)} />
        </label>
        <label className="field">
          <span>Attributes (key=value per line)</span>
          <textarea
            className="input mono"
            rows={2}
            value={attrs}
            onChange={(e) => setAttrs(e.target.value)}
          />
        </label>
        <button className="btn primary" disabled={!userId.trim()}>
          Evaluate
        </button>
      </form>

      {error && <p className="msg bad">{error}</p>}

      {result && (
        <div className="result">
          <div className="result-head">
            <span className={`verdict ${result.enabled ? "on" : "off"}`}>
              {result.enabled ? "ON" : "OFF"}
            </span>
            <span className="muted small">
              {REASONS[result.reason]} · {result.cached ? "cache hit" : "computed"} ·{" "}
              {latency?.toFixed(1)} ms
            </span>
          </div>
          {result.bucket !== null && (
            <BucketBar bucket={result.bucket} cutoff={flag.rollout_percentage} />
          )}
        </div>
      )}
    </div>
  );
}

function BucketBar({ bucket, cutoff }) {
  return (
    <div className="bucket">
      <div className="bucket-track">
        <span className="bucket-included" style={{ width: `${cutoff}%` }} />
        <span className="bucket-marker" style={{ left: `${bucket + 0.5}%` }} />
      </div>
      <div className="bucket-legend small muted">
        <span>
          bucket <strong>{bucket}</strong> {bucket < cutoff ? "<" : "≥"} cutoff{" "}
          <strong>{cutoff}</strong>
        </span>
        <span>0 – 99</span>
      </div>
    </div>
  );
}
