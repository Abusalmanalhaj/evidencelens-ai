import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import type { Project } from "../types";

export default function ProjectsPage() {
  const { token } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", sector: "", stage: "" });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    api.getProjects(token).then((r) => setProjects(r.items)).finally(() => setLoading(false));
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setCreating(true);
    try {
      const project = await api.createProject(token, form);
      setProjects((prev) => [project, ...prev]);
      setShowCreate(false);
      setForm({ name: "", description: "", sector: "", stage: "" });
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Diligence Projects</h1>
          <p className="text-slate-500 mt-1">Analyze startup pitch decks with AI-powered evidence mapping</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="bg-brand-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-brand-700 transition-colors">
          New Project
        </button>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <form onSubmit={handleCreate} className="bg-white rounded-xl p-6 w-full max-w-md space-y-4 shadow-xl">
            <h2 className="text-lg font-semibold">Create Project</h2>
            <input required placeholder="Startup name" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-brand-500" />
            <textarea placeholder="Description" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-brand-500" rows={3} />
            <input placeholder="Sector (e.g. AI, FinTech)" value={form.sector}
              onChange={(e) => setForm({ ...form, sector: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-brand-500" />
            <input placeholder="Stage (e.g. Seed, Series A)" value={form.stage}
              onChange={(e) => setForm({ ...form, stage: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg outline-none focus:ring-2 focus:ring-brand-500" />
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-slate-600">Cancel</button>
              <button type="submit" disabled={creating} className="bg-brand-600 text-white px-4 py-2 rounded-lg disabled:opacity-50">
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Create your first diligence project to analyze a startup pitch deck."
          action={
            <button onClick={() => setShowCreate(true)} className="bg-brand-600 text-white px-4 py-2 rounded-lg">
              Create Project
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:border-brand-300 hover:shadow-sm transition-all">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-slate-900">{p.name}</h3>
                <StatusBadge status={p.analysis_status} />
              </div>
              {p.sector && <p className="text-xs text-slate-500 mb-1">{p.sector} · {p.stage || "Unknown stage"}</p>}
              {p.description && <p className="text-sm text-slate-600 line-clamp-2">{p.description}</p>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
