const BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ")
      : body.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return body;
}

export const api = {
  health: () => request("/health"),
  listFlags: () => request("/api/v1/flags"),
  createFlag: (data) => request("/api/v1/flags", { method: "POST", body: JSON.stringify(data) }),
  updateFlag: (key, data) =>
    request(`/api/v1/flags/${key}`, { method: "PATCH", body: JSON.stringify(data) }),
  toggleFlag: (key) => request(`/api/v1/flags/${key}/toggle`, { method: "POST" }),
  deleteFlag: (key) => request(`/api/v1/flags/${key}`, { method: "DELETE" }),
  evaluate: (flagKey, userId, attributes) =>
    request("/api/v1/evaluate", {
      method: "POST",
      body: JSON.stringify({ flag_key: flagKey, user_id: userId, attributes }),
    }),
  audit: (flagKey, limit = 20) =>
    request(`/api/v1/audit?limit=${limit}${flagKey ? `&flag_key=${flagKey}` : ""}`),
};
