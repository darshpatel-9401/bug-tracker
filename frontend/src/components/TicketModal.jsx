import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { PRIORITIES, STATUSES, TYPES, label } from "../constants";
import Attachments from "./Attachments";
import Comments from "./Comments";

export default function TicketModal({
  ticket, // null means "create a new ticket"
  defaultStatus = "todo",
  project,
  currentUser,
  canEdit,
  isAdmin,
  onClose,
  onSaved,
  onDeleted,
}) {
  const isNew = ticket === null;
  const [form, setForm] = useState({
    title: ticket?.title ?? "",
    description: ticket?.description ?? "",
    type: ticket?.type ?? "bug",
    priority: ticket?.priority ?? "medium",
    status: ticket?.status ?? defaultStatus,
    assignee_id: ticket?.assignee ? String(ticket.assignee.id) : "",
  });
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  // Only developers and admins can be assigned work.
  const assignable = project.members.filter((m) => m.role !== "viewer");
  const canDelete = !isNew && (isAdmin || (canEdit && ticket.reporter.id === currentUser.id));

  useEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set = (key) => (event) => {
    setSaved(false);
    setForm((current) => ({ ...current, [key]: event.target.value }));
  };

  async function handleSave(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const payload = {
      title: form.title,
      description: form.description || null,
      type: form.type,
      priority: form.priority,
      status: form.status,
      assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
    };
    try {
      const { data } = isNew
        ? await api.post(`/projects/${project.id}/tickets`, payload)
        : await api.patch(`/tickets/${ticket.id}`, payload);
      onSaved(data, isNew);
      if (isNew) onClose();
      else setSaved(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this ticket, its comments and its attachments? This cannot be undone.")) return;
    try {
      await api.delete(`/tickets/${ticket.id}`);
      onDeleted(ticket.id);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/50 p-4"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <div className="panel my-8 w-full max-w-3xl p-6" role="dialog" aria-modal="true">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {isNew ? "New ticket" : <><span className="mr-2 font-mono text-muted">#{ticket.id}</span>Ticket</>}
          </h2>
          <button className="btn" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="label" htmlFor="t-title">Title</label>
            <input id="t-title" required maxLength={200} disabled={!canEdit} className="input" value={form.title} onChange={set("title")} />
          </div>
          <div>
            <label className="label" htmlFor="t-desc">Description</label>
            <textarea id="t-desc" rows={5} maxLength={10000} disabled={!canEdit} className="input" value={form.description} onChange={set("description")} />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <label className="label" htmlFor="t-type">Type</label>
              <select id="t-type" disabled={!canEdit} className="input" value={form.type} onChange={set("type")}>
                {TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="t-pri">Priority</label>
              <select id="t-pri" disabled={!canEdit} className="input" value={form.priority} onChange={set("priority")}>
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="t-status">Status</label>
              <select id="t-status" disabled={!canEdit} className="input" value={form.status} onChange={set("status")}>
                {STATUSES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="t-assignee">Assignee</label>
              <select id="t-assignee" disabled={!canEdit} className="input" value={form.assignee_id} onChange={set("assignee_id")}>
                <option value="">Unassigned</option>
                {assignable.map((m) => <option key={m.user.id} value={m.user.id}>{m.user.full_name}</option>)}
              </select>
            </div>
          </div>

          {!isNew && (
            <p className="text-xs text-muted">
              Reported by {ticket.reporter.full_name} on {new Date(ticket.created_at).toLocaleString()}
            </p>
          )}
          {error && <p className="text-sm text-red-700">{error}</p>}

          <div className="flex items-center gap-2">
            {canEdit && (
              <button className="btn btn-primary" disabled={busy}>
                {busy ? "Saving…" : isNew ? "Create ticket" : "Save changes"}
              </button>
            )}
            {saved && <span className="text-sm text-emerald-700">Saved ✓</span>}
            {canDelete && (
              <button type="button" className="btn btn-danger ml-auto" onClick={handleDelete}>
                Delete
              </button>
            )}
          </div>
        </form>

        {!isNew && (
          <div className="mt-6 space-y-6 border-t border-line pt-6">
            <Attachments ticketId={ticket.id} canUpload={canEdit} currentUser={currentUser} isAdmin={isAdmin} />
            <Comments ticketId={ticket.id} canComment={canEdit} currentUser={currentUser} isAdmin={isAdmin} />
          </div>
        )}
      </div>
    </div>
  );
}
