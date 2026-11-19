import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ROLE_STYLES } from "../constants";
import FilterBar from "../components/FilterBar";
import KanbanBoard from "../components/KanbanBoard";
import MembersPanel from "../components/MembersPanel";
import TicketModal from "../components/TicketModal";

export default function ProjectBoard() {
  const { projectId } = useParams();
  const { user } = useAuth();

  const [project, setProject] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showTeam, setShowTeam] = useState(false);

  const [search, setSearch] = useState("");
  const [query, setQuery] = useState(""); // the debounced version of `search`
  const [filters, setFilters] = useState({ type: "", priority: "", assignee_id: "" });

  // null = closed, { ticket } = editing/viewing, { ticket: null, status } = creating
  const [modal, setModal] = useState(null);

  const loadProject = useCallback(async () => {
    try {
      const { data } = await api.get(`/projects/${projectId}`);
      setProject(data);
    } catch (err) {
      setError(err.response?.status === 404 ? "Project not found." : errorMessage(err));
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // Wait until the person stops typing before hitting the API.
  useEffect(() => {
    const timer = setTimeout(() => setQuery(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    const params = { limit: 200 };
    if (query) params.q = query;
    if (filters.type) params.type = filters.type;
    if (filters.priority) params.priority = filters.priority;
    if (filters.assignee_id) params.assignee_id = filters.assignee_id;

    api
      .get(`/projects/${projectId}/tickets`, { params })
      .then((res) => {
        if (cancelled) return;
        setTickets(res.data.items);
        setTotal(res.data.total);
      })
      .catch((err) => !cancelled && setError(errorMessage(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [projectId, query, filters]);

  // Drag-and-drop: update the screen straight away, then tell the server.
  // If the server says no, put the card back and show why.
  async function moveTicket(ticketId, status) {
    const before = tickets;
    setTickets((current) => current.map((t) => (t.id === ticketId ? { ...t, status } : t)));
    try {
      const { data } = await api.patch(`/tickets/${ticketId}`, { status });
      setTickets((current) => current.map((t) => (t.id === ticketId ? data : t)));
    } catch (err) {
      setTickets(before);
      setError(errorMessage(err));
    }
  }

  function handleSaved(saved, isNew) {
    if (isNew) {
      setTickets((current) => [saved, ...current]);
      setTotal((n) => n + 1);
    } else {
      setTickets((current) => current.map((t) => (t.id === saved.id ? saved : t)));
    }
  }

  function handleDeleted(ticketId) {
    setTickets((current) => current.filter((t) => t.id !== ticketId));
    setTotal((n) => n - 1);
  }

  if (!project) {
    return error ? (
      <div className="panel p-8 text-center">
        <p className="mb-3 text-red-700">{error}</p>
        <Link className="btn" to="/">Back to projects</Link>
      </div>
    ) : (
      <p className="text-muted">Loading…</p>
    );
  }

  const isAdmin = project.my_role === "admin";
  const canEdit = project.my_role !== "viewer";
  const assignees = project.members.filter((m) => m.role !== "viewer");

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link to="/" className="text-sm text-muted hover:text-ink">← Projects</Link>
        <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${ROLE_STYLES[project.my_role]}`}>{project.my_role}</span>
        <div className="ml-auto flex gap-2">
          <button className="btn" onClick={() => setShowTeam(!showTeam)}>
            Team ({project.members.length})
          </button>
          {canEdit && (
            <button className="btn btn-primary" onClick={() => setModal({ ticket: null, status: "todo" })}>
              New ticket
            </button>
          )}
        </div>
      </div>

      {project.description && <p className="mb-4 max-w-3xl text-sm text-muted">{project.description}</p>}
      {showTeam && <MembersPanel project={project} isAdmin={isAdmin} currentUser={user} onChanged={loadProject} />}

      <FilterBar search={search} onSearch={setSearch} filters={filters} onFilters={setFilters} assignees={assignees} />

      {error && (
        <p className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}{" "}
          <button className="underline" onClick={() => setError("")}>dismiss</button>
        </p>
      )}
      {total > tickets.length && (
        <p className="mb-3 text-sm text-muted">
          Showing the newest {tickets.length} of {total} tickets. Use the filters to narrow it down.
        </p>
      )}

      {loading ? (
        <p className="text-muted">Loading tickets…</p>
      ) : (
        <KanbanBoard
          tickets={tickets}
          canEdit={canEdit}
          onMove={moveTicket}
          onOpen={(ticket) => setModal({ ticket })}
          onAdd={(status) => setModal({ ticket: null, status })}
        />
      )}

      {modal && (
        <TicketModal
          key={modal.ticket ? modal.ticket.id : "new"}
          ticket={modal.ticket}
          defaultStatus={modal.status}
          project={project}
          currentUser={user}
          canEdit={canEdit}
          isAdmin={isAdmin}
          onClose={() => setModal(null)}
          onSaved={handleSaved}
          onDeleted={handleDeleted}
        />
      )}
    </div>
  );
}
