import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { ROLE_STYLES } from "../constants";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api
      .get("/projects")
      .then((res) => setProjects(res.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    setCreating(true);
    try {
      const { data } = await api.post("/projects", { name, description: description || null });
      setProjects((current) => [data, ...current]);
      setName("");
      setDescription("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
      <section>
        <h1 className="mb-4 text-2xl font-semibold tracking-tight">Your projects</h1>
        {error && <p className="mb-3 text-sm text-red-700">{error}</p>}
        {loading ? (
          <p className="text-muted">Loading…</p>
        ) : projects.length === 0 ? (
          <div className="panel p-8 text-center text-muted">
            No projects yet. Create your first one to start tracking tickets.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="panel block p-4 transition hover:border-signal"
              >
                <div className="flex items-start justify-between gap-2">
                  <h2 className="font-semibold">{project.name}</h2>
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${ROLE_STYLES[project.my_role]}`}>
                    {project.my_role}
                  </span>
                </div>
                {project.description && (
                  <p className="mt-2 line-clamp-2 text-sm text-muted">{project.description}</p>
                )}
              </Link>
            ))}
          </div>
        )}
      </section>

      <aside>
        <form onSubmit={handleCreate} className="panel space-y-3 p-4">
          <h2 className="font-semibold">New project</h2>
          <div>
            <label className="label" htmlFor="pname">Name</label>
            <input id="pname" required maxLength={120} className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="pdesc">Description</label>
            <textarea id="pdesc" rows={3} className="input" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <button className="btn btn-primary w-full" disabled={creating}>
            {creating ? "Creating…" : "Create project"}
          </button>
        </form>
      </aside>
    </div>
  );
}
