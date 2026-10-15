import { useState } from "react";
import { api } from "../api.js";

const slugify = (text) =>
  text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);

export default function CreateFlagModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [keyTouched, setKeyTouched] = useState(false);
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const effectiveKey = keyTouched ? key : slugify(name);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const flag = await api.createFlag({
        key: effectiveKey,
        name,
        description,
        enabled: false,
        rollout_percentage: 0,
      });
      onCreated(flag);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overlay" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h2>New feature flag</h2>
        <label className="field">
          <span>Name</span>
          <input
            autoFocus
            className="input"
            placeholder="New checkout flow"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Key (used by your code)</span>
          <input
            className="input mono"
            value={effectiveKey}
            onChange={(e) => {
              setKeyTouched(true);
              setKey(e.target.value);
            }}
          />
        </label>
        <label className="field">
          <span>Description</span>
          <textarea
            className="input"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <p className="hint">New flags start off at 0% rollout so nothing ships by accident.</p>
        {error && <p className="msg bad">{error}</p>}
        <div className="actions">
          <button type="button" className="btn ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={!name || !effectiveKey || busy}>
            Create flag
          </button>
        </div>
      </form>
    </div>
  );
}
