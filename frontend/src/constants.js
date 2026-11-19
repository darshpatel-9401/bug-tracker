export const STATUSES = [
  { id: "todo", label: "To do" },
  { id: "in_progress", label: "In progress" },
  { id: "in_review", label: "In review" },
  { id: "done", label: "Done" },
];

export const TYPES = ["bug", "task", "feature"];
export const PRIORITIES = ["low", "medium", "high", "critical"];
export const ROLES = ["admin", "developer", "viewer"];

export const PRIORITY_STYLES = {
  low: "bg-stone-200 text-stone-700",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-200 text-orange-900",
  critical: "bg-red-600 text-white",
};

export const TYPE_STYLES = {
  bug: "text-red-700",
  task: "text-sky-700",
  feature: "text-emerald-700",
};

export const ROLE_STYLES = {
  admin: "bg-ink text-paper",
  developer: "bg-signal/15 text-signal-dark",
  viewer: "bg-stone-200 text-stone-700",
};

export const label = (value) => value.replace("_", " ");

export const initials = (name) =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
