import { useState } from "react";
import { api } from "../api.js";
import Toggle from "./Toggle.jsx";
import RulesEditor from "./RulesEditor.jsx";
import EvaluatePanel from "./EvaluatePanel.jsx";
import AuditLog from "./AuditLog.jsx";

const toForm = (flag) => ({
  name: flag.name,
  description: flag.description,
  rollout_percentage: flag.rollout_percentage,
  targeted_users: flag.targeted_users.join(", "),
  rules: flag.rules.map((r) => ({ ...r, values: r.values.join(", ") })),
});

const splitList = (text) =>
  text
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);

export default function FlagEditor({ flag, onSaved, onDeleted, onToggle }) {
  const [form, setForm] = useState(() => toForm(flag));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const set = (field) => (value) => setForm((f) => ({ ...f, [field]: value }));
  const dirty = JSON.stringify(form) !== JSON.stringify(toForm(flag));

  const save = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateFlag(flag.key, {
        name: form.name,
        description: form.description,
        rollout_percentage: Number(form.rollout_percentage),
        targeted_users: splitList(form.targeted_users),
        rules: form.rules.map((r) => ({ ...r, values: splitList(r.values) })),
      });
      onSaved(updated);
      setForm(toForm(updated));
      setMessage({ type: "good", text: `Saved · version ${updated.version}` });
    } catch (e) {
      setMessage({ type: "bad", text: e.message });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete flag "${flag.key}"? SDKs will start receiving 404s.`)) return;
    try {
      await api.deleteFlag(flag.key);
      onDeleted(flag.key);
    } catch (e) {
      setMessage({ type: "bad", text: e.message });
    }
  };

  return (
    <div className="editor">
      <div className="editor-head">
        <div>
          <code className="flag-key big">{flag.key}</code>
          <h1>{flag.name}</h1>
          <p className="muted small">
            v{flag.version} · updated {new Date(flag.updated_at).toLocaleString()}
          </p>
        </div>
        <div className="kill-switch">
          <span className={flag.enabled ? "status on" : "status"}>
            {flag.enabled ? "Serving" : "Off for everyone"}
          </span>
          <Toggle checked={flag.enabled} onChange={onToggle} label="Kill switch" />
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h2>Configuration</h2>
          <label className="field">
            <span>Name</span>
            <input className="input" value={form.name} onChange={(e) => set("name")(e.target.value)} />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              className="input"
              rows={2}
              value={form.description}
              onChange={(e) => set("description")(e.target.value)}
            />
          </label>

          <div className="field">
            <span>
              Percentage rollout <strong className="accent">{form.rollout_percentage}%</strong>
            </span>
            <input
              type="range"
              min="0"
              max="100"
              value={form.rollout_percentage}
              onChange={(e) => set("rollout_percentage")(Number(e.target.value))}
            />
            <p className="hint">
              Users whose bucket MD5(key:user_id) % 100 is below this value get the flag.
              Raising it never removes users who already have it.
            </p>
          </div>

          <label className="field">
            <span>Always-on users</span>
            <textarea
              className="input mono"
              rows={2}
              placeholder="user_1, qa_team"
              value={form.targeted_users}
              onChange={(e) => set("targeted_users")(e.target.value)}
            />
          </label>

          <RulesEditor rules={form.rules} onChange={set("rules")} />

          <div className="actions">
            <button className="btn primary" disabled={!dirty || saving} onClick={save}>
              {saving ? "Saving…" : "Save changes"}
            </button>
            <button className="btn ghost" disabled={!dirty} onClick={() => setForm(toForm(flag))}>
              Reset
            </button>
            <span className="spacer" />
            <button className="btn danger" onClick={remove}>
              Delete
            </button>
          </div>
          {message && <p className={`msg ${message.type}`}>{message.text}</p>}
        </div>

        <div className="stack">
          <EvaluatePanel flag={flag} />
          <AuditLog flagKey={flag.key} version={flag.version} />
        </div>
      </div>
    </div>
  );
}
