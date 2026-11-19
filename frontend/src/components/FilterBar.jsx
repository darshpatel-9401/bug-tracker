import { PRIORITIES, TYPES, label } from "../constants";

export default function FilterBar({ search, onSearch, filters, onFilters, assignees }) {
  const set = (key) => (event) => onFilters({ ...filters, [key]: event.target.value });
  const active = search || filters.type || filters.priority || filters.assignee_id;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <input
        className="input max-w-xs"
        placeholder="Search title or description…"
        value={search}
        onChange={(e) => onSearch(e.target.value)}
        maxLength={100}
      />
      <select className="input w-auto" value={filters.type} onChange={set("type")}>
        <option value="">All types</option>
        {TYPES.map((t) => (
          <option key={t} value={t}>{label(t)}</option>
        ))}
      </select>
      <select className="input w-auto" value={filters.priority} onChange={set("priority")}>
        <option value="">All priorities</option>
        {PRIORITIES.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>
      <select className="input w-auto" value={filters.assignee_id} onChange={set("assignee_id")}>
        <option value="">Anyone</option>
        {assignees.map((m) => (
          <option key={m.user.id} value={m.user.id}>{m.user.full_name}</option>
        ))}
      </select>
      {active && (
        <button
          className="btn"
          onClick={() => {
            onSearch("");
            onFilters({ type: "", priority: "", assignee_id: "" });
          }}
        >
          Clear
        </button>
      )}
    </div>
  );
}
