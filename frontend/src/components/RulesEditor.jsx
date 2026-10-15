const OPERATORS = [
  ["equals", "equals"],
  ["not_equals", "does not equal"],
  ["in", "is one of"],
  ["not_in", "is not one of"],
  ["gt", "greater than"],
  ["lt", "less than"],
];

export default function RulesEditor({ rules, onChange }) {
  const update = (index, field, value) =>
    onChange(rules.map((r, i) => (i === index ? { ...r, [field]: value } : r)));
  const add = () => onChange([...rules, { attribute: "", operator: "equals", values: "" }]);
  const remove = (index) => onChange(rules.filter((_, i) => i !== index));

  return (
    <div className="field">
      <span>Targeting rules</span>
      <p className="hint">Users matching any rule get the flag, regardless of rollout.</p>
      {rules.map((rule, i) => (
        <div className="rule-row" key={i}>
          <input
            className="input mono"
            placeholder="attribute"
            value={rule.attribute}
            onChange={(e) => update(i, "attribute", e.target.value)}
          />
          <select
            className="input"
            value={rule.operator}
            onChange={(e) => update(i, "operator", e.target.value)}
          >
            {OPERATORS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            className="input mono"
            placeholder="IN, US"
            value={rule.values}
            onChange={(e) => update(i, "values", e.target.value)}
          />
          <button className="btn ghost icon" aria-label="Remove rule" onClick={() => remove(i)}>
            ×
          </button>
        </div>
      ))}
      <button className="btn ghost small" onClick={add}>
        + Add rule
      </button>
    </div>
  );
}
