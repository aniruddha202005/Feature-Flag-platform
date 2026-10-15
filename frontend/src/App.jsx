import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import FlagList from "./components/FlagList.jsx";
import FlagEditor from "./components/FlagEditor.jsx";
import CreateFlagModal from "./components/CreateFlagModal.jsx";

export default function App() {
  const [flags, setFlags] = useState([]);
  const [selectedKey, setSelectedKey] = useState(null);
  const [health, setHealth] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  const refresh = useCallback(async () => {
    try {
      const list = await api.listFlags();
      setFlags(list);
      setError("");
      setSelectedKey((current) =>
        current && list.some((f) => f.key === current) ? current : list[0]?.key ?? null,
      );
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const loadHealth = () => api.health().then(setHealth).catch(() => setHealth(null));
    loadHealth();
    const id = setInterval(loadHealth, 10000);
    return () => clearInterval(id);
  }, [refresh]);

  const replaceFlag = (updated) =>
    setFlags((list) => list.map((f) => (f.key === updated.key ? updated : f)));

  const handleToggle = async (key) => {
    try {
      replaceFlag(await api.toggleFlag(key));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleCreated = (flag) => {
    setFlags((list) => [flag, ...list]);
    setSelectedKey(flag.key);
    setShowCreate(false);
  };

  const handleDeleted = (key) => {
    const remaining = flags.filter((f) => f.key !== key);
    setFlags(remaining);
    setSelectedKey(remaining[0]?.key ?? null);
  };

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return flags;
    return flags.filter((f) => f.key.includes(q) || f.name.toLowerCase().includes(q));
  }, [flags, query]);

  const selected = flags.find((f) => f.key === selectedKey) || null;
  const enabledCount = flags.filter((f) => f.enabled).length;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>Flagpole</span>
        </div>
        <div className="topbar-meta">
          <span>
            {flags.length} flags · {enabledCount} on
          </span>
          <HealthBadge health={health} />
        </div>
      </header>

      {error && (
        <div className="banner" role="alert">
          {error}
          <button className="link" onClick={() => setError("")}>
            dismiss
          </button>
        </div>
      )}

      <main className="layout">
        <aside className="sidebar">
          <div className="sidebar-head">
            <input
              className="input"
              placeholder="Search flags"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button className="btn primary" onClick={() => setShowCreate(true)}>
              New flag
            </button>
          </div>
          <FlagList
            flags={visible}
            selectedKey={selectedKey}
            onSelect={setSelectedKey}
            onToggle={handleToggle}
          />
        </aside>

        <section className="content">
          {selected ? (
            <FlagEditor
              key={selected.key}
              flag={selected}
              onSaved={replaceFlag}
              onDeleted={handleDeleted}
              onToggle={() => handleToggle(selected.key)}
            />
          ) : (
            <div className="empty">
              <h2>No flag selected</h2>
              <p>Create your first flag to start controlling rollouts.</p>
              <button className="btn primary" onClick={() => setShowCreate(true)}>
                New flag
              </button>
            </div>
          )}
        </section>
      </main>

      {showCreate && (
        <CreateFlagModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}

function HealthBadge({ health }) {
  if (!health) return <span className="pill bad">API offline</span>;
  if (health.status === "ok") return <span className="pill good">All systems normal</span>;
  return (
    <span className="pill warn">
      Degraded · {health.redis ? "" : "Redis down"}
      {health.database ? "" : " DB down"}
    </span>
  );
}
