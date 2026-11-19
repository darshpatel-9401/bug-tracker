import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { ROLES, ROLE_STYLES, initials } from "../constants";

export default function MembersPanel({ project, isAdmin, currentUser, onChanged }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("developer");
  const [error, setError] = useState("");

  async function run(action) {
    setError("");
    try {
      await action();
      await onChanged();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const addMember = (event) => {
    event.preventDefault();
    run(async () => {
      await api.post(`/projects/${project.id}/members`, { email, role });
      setEmail("");
    });
  };

  return (
    <div className="panel mb-4 p-4">
      <h2 className="mb-3 font-semibold">Team</h2>
      <ul className="divide-y divide-line">
        {project.members.map((m) => (
          <li key={m.user.id} className="flex items-center gap-3 py-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink font-mono text-xs text-paper">
              {initials(m.user.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">
                {m.user.full_name} {m.user.id === currentUser.id && <span className="text-muted">(you)</span>}
              </p>
              <p className="truncate text-xs text-muted">{m.user.email}</p>
            </div>
            {isAdmin ? (
              <>
                <select
                  className="input w-auto py-1"
                  value={m.role}
                  onChange={(e) => run(() => api.patch(`/projects/${project.id}/members/${m.user.id}`, { role: e.target.value }))}
                >
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <button
                  className="btn btn-danger py-1"
                  onClick={() => window.confirm(`Remove ${m.user.full_name} from this project?`) && run(() => api.delete(`/projects/${project.id}/members/${m.user.id}`))}
                >
                  Remove
                </button>
              </>
            ) : (
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${ROLE_STYLES[m.role]}`}>{m.role}</span>
            )}
          </li>
        ))}
      </ul>
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      {isAdmin && (
        <form onSubmit={addMember} className="mt-4 flex flex-wrap items-end gap-2 border-t border-line pt-4">
          <div className="min-w-[220px] flex-1">
            <label className="label" htmlFor="m-email">Add by email</label>
            <input id="m-email" type="email" required className="input" placeholder="teammate@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="m-role">Role</label>
            <select id="m-role" className="input" value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <button className="btn btn-primary">Add member</button>
        </form>
      )}
    </div>
  );
}
