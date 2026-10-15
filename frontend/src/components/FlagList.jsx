import Toggle from "./Toggle.jsx";

export default function FlagList({ flags, selectedKey, onSelect, onToggle }) {
  if (!flags.length) return <p className="muted pad">No flags match.</p>;

  return (
    <ul className="flag-list">
      {flags.map((flag) => (
        <li key={flag.key}>
          <div
            role="button"
            tabIndex={0}
            className={`flag-row ${flag.key === selectedKey ? "selected" : ""}`}
            onClick={() => onSelect(flag.key)}
            onKeyDown={(e) => e.key === "Enter" && onSelect(flag.key)}
          >
            <div className="flag-row-main">
              <span className="flag-name">{flag.name}</span>
              <code className="flag-key">{flag.key}</code>
              <div className="mini-bar" aria-hidden="true">
                <span style={{ width: `${flag.enabled ? flag.rollout_percentage : 0}%` }} />
              </div>
            </div>
            <div className="flag-row-side">
              <Toggle
                checked={flag.enabled}
                onChange={() => onToggle(flag.key)}
                label={`Toggle ${flag.key}`}
              />
              <span className="muted small">{flag.rollout_percentage}%</span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
