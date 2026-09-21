import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import type { AnalysisStatus, Document, Project } from "../types";
import AnalyticsDashboard from "../components/AnalyticsDashboard";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { token } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [analysisApiKey, setAnalysisApiKey] = useState("");
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"upload" | "analytics" | "claims">("upload");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    const [p, docs, status] = await Promise.all([
      api.getProject(token, projectId),
      api.getDocuments(token, projectId),
      api.getAnalysisStatus(token, projectId),
    ]);
    setProject(p);
    setDocuments(docs);
    setAnalysisStatus(status);
    setSelectedDocumentId((current) => {
      if (current && docs.some((doc) => doc.id === current && doc.status === "extracted")) return current;
      return docs.find((doc) => doc.status === "extracted")?.id ?? null;
    });
  }, [token, projectId]);

  useEffect(() => {
    if (!token) return;
    refresh().catch((err) => {
      setError(err instanceof Error ? err.message : "Unable to load project status");
    }).finally(() => setLoading(false));
  }, [token, refresh]);

  useEffect(() => {
    const projectInProgress = project?.analysis_status === "uploading"
      || project?.analysis_status === "extracting"
      || project?.analysis_status === "analyzing";
    const runInProgress = analysisStatus?.current_run?.status === "pending"
      || analysisStatus?.current_run?.status === "running";
    const documentInProgress = documents.some((doc) => doc.status === "processing");
    const inProgress = projectInProgress || runInProgress || documentInProgress;

    if (pollRef.current) clearInterval(pollRef.current);
    if (inProgress) {
      pollRef.current = setInterval(() => {
        refresh().catch((err) => {
          setError(err instanceof Error ? err.message : "Unable to refresh analysis status");
        });
      }, 3000);
    } else {
    }

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [analysisStatus?.current_run?.status, documents, project?.analysis_status, refresh]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadDocument(token, projectId, file);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!token || !selectedDocumentId) return;
    setError("");
    try {
      await api.startAnalysis(token, projectId, selectedDocumentId, analysisApiKey.trim() || undefined);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    }
  };

  const handleDownloadReport = async () => {
    if (!token) return;
    const res = await api.downloadReport(token, projectId);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evidencelens-report-${projectId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <LoadingSpinner />;
  if (!project) return <div>Project not found</div>;

  const selectedDocument = documents.find((doc) => doc.id === selectedDocumentId);
  const workflowStatus = getWorkflowStatus(
    project.analysis_status,
    documents,
    analysisStatus?.current_run?.status,
  );
  const analysisInProgress = workflowStatus === "extracting" || workflowStatus === "analyzing";

  return (
    <div>
      <div className="mb-6">
        <Link to="/" className="text-sm text-brand-600 hover:underline">← Back to projects</Link>
        <div className="flex items-start justify-between mt-2">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{project.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={workflowStatus} />
              {analysisStatus && !analysisStatus.llm_enabled && (
                <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">
                  Heuristic mode (no OpenAI key)
                </span>
              )}
            </div>
          </div>
          {workflowStatus === "completed" && (
            <button onClick={handleDownloadReport}
              className="bg-white border border-slate-300 px-4 py-2 rounded-lg text-sm hover:bg-slate-50">
              Download Report
            </button>
          )}
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-700 p-3 rounded-lg mb-4 text-sm">{error}</div>}
      {project.error_message && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg mb-4 text-sm">{project.error_message}</div>
      )}

      <WorkflowProgress status={workflowStatus} />

      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {(["upload", "analytics", "claims"] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
              activeTab === tab ? "border-brand-600 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}>
            {tab === "upload" ? "Documents" : tab === "analytics" ? "Overview" : "Claims"}
          </button>
        ))}
      </div>

      {activeTab === "upload" && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="font-semibold mb-4">Upload Pitch Deck (PDF)</h2>
            <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:border-brand-400 hover:bg-brand-50/30 transition-colors">
              <input type="file" accept=".pdf,application/pdf" onChange={handleUpload} className="hidden" disabled={uploading} />
              <svg className="w-10 h-10 text-slate-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-sm text-slate-600">{uploading ? "Uploading..." : "Click to upload PDF (max 25MB)"}</span>
            </label>
          </div>

          {documents.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h2 className="font-semibold">Your documents</h2>
                  <p className="text-sm text-slate-500 mt-1">Choose one extracted PDF before starting analysis.</p>
                </div>
                <span className="text-xs text-slate-400">{documents.length} uploaded</span>
              </div>
              <ul className="space-y-2">
                {documents.map((d) => (
                  <li key={d.id} className={`flex items-center justify-between gap-4 py-3 px-3 border rounded-lg ${selectedDocumentId === d.id ? "border-brand-400 bg-brand-50/40" : "border-slate-100"}`}>
                    <label className={`flex items-center gap-3 min-w-0 ${d.status === "extracted" ? "cursor-pointer" : "cursor-default"}`}>
                      <input
                        type="radio"
                        name="analysis-document"
                        checked={selectedDocumentId === d.id}
                        onChange={() => setSelectedDocumentId(d.id)}
                        disabled={d.status !== "extracted" || analysisInProgress}
                        className="accent-brand-600"
                      />
                      <span className="text-sm truncate" title={d.filename}>{d.filename}</span>
                    </label>
                    <div className="flex items-center gap-2">
                      {d.page_count && <span className="text-xs text-slate-500">{d.page_count} pages</span>}
                      <StatusBadge status={d.status} />
                    </div>
                    {d.error_message && <p className="basis-full text-xs text-red-600">{d.error_message}</p>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selectedDocument && (
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="font-semibold mb-2">Run Analysis</h2>
              <p className="text-sm text-slate-500 mb-4">
                Analyze <span className="font-medium text-slate-700">{selectedDocument.filename}</span> to extract claims and map evidence.
              </p>
              <label className="block mb-4">
                <span className="text-sm font-medium text-slate-700">OpenAI API key (optional)</span>
                <input
                  type="password"
                  value={analysisApiKey}
                  onChange={(e) => setAnalysisApiKey(e.target.value)}
                  placeholder="Use a personal key for this analysis"
                  autoComplete="off"
                  spellCheck={false}
                  className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                  disabled={analysisInProgress}
                />
                <span className="block text-xs text-slate-500 mt-1">
                  Sent only for this run and never saved by EvidenceLens.
                </span>
              </label>
              <button onClick={handleAnalyze} disabled={analysisInProgress}
                className="bg-brand-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-brand-700 disabled:opacity-50">
                {analysisInProgress ? "Analyzing..." : "Start Analysis"}
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === "analytics" && (
        <AnalyticsDashboard projectId={projectId} />
      )}

      {activeTab === "claims" && (
        <ClaimsList projectId={projectId} />
      )}
    </div>
  );
}

function getWorkflowStatus(
  projectStatus: string,
  documents: Document[],
  runStatus?: string,
): "uploaded" | "extracting" | "analyzing" | "completed" | "failed" {
  if (projectStatus === "failed" || runStatus === "failed") return "failed";
  if (projectStatus === "completed" || runStatus === "completed") return "completed";
  if (documents.some((doc) => doc.status === "processing") || projectStatus === "extracting") {
    return "extracting";
  }
  if (projectStatus === "analyzing" || runStatus === "pending" || runStatus === "running") {
    return "analyzing";
  }
  return "uploaded";
}

function WorkflowProgress({ status }: { status: ReturnType<typeof getWorkflowStatus> }) {
  const stage = status;
  const stages = [
    { key: "uploaded", label: "Uploaded" },
    { key: "extracting", label: "Extract text" },
    { key: "analyzing", label: "Analyze" },
    { key: "completed", label: "Complete" },
  ];
  const currentIndex = Math.max(0, stages.findIndex((item) => item.key === stage));
  const failed = stage === "failed";

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <p className="text-sm font-semibold text-slate-800">Workflow status</p>
          <p className="text-xs text-slate-500 mt-0.5">
            {failed ? "Something needs attention." : stage === "uploaded" ? "PDF is ready. Choose it and start analysis." : stage === "completed" ? "Your analysis is ready." : `Current step: ${stage === "extracting" ? "extracting text" : stage}.`}
          </p>
        </div>
        <StatusBadge status={failed ? "failed" : stage} />
      </div>
      <div className="grid grid-cols-4 gap-2">
        {stages.map((item, index) => (
          <div key={item.key} className="flex items-center gap-2 min-w-0">
            <span className={`w-6 h-6 shrink-0 rounded-full flex items-center justify-center text-xs font-semibold ${failed && index === currentIndex ? "bg-red-100 text-red-700" : index <= currentIndex ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-400"}`}>
              {index + 1}
            </span>
            <span className={`text-xs truncate ${index <= currentIndex ? "text-slate-700" : "text-slate-400"}`}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClaimsList({ projectId }: { projectId: number }) {
  const { token } = useAuth();
  const [claims, setClaims] = useState<import("../types").Claim[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api.getClaims(token, projectId).then((r) => setClaims(r.items)).finally(() => setLoading(false));
  }, [token, projectId]);

  if (loading) return <LoadingSpinner />;
  if (claims.length === 0) return (
    <div className="text-center py-12 text-slate-500">No claims extracted yet. Upload a deck and run analysis.</div>
  );

  return (
    <div className="space-y-3">
      {claims.map((c) => (
        <Link key={c.id} to={`/projects/${projectId}/claims/${c.id}`}
          className="block bg-white rounded-xl border border-slate-200 p-4 hover:border-brand-300 transition-colors">
          <div className="flex items-start justify-between gap-4">
            <p className="text-sm text-slate-800 flex-1">{c.text}</p>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs bg-slate-100 px-2 py-0.5 rounded">{c.category}</span>
              {c.assessment && <StatusBadge status={c.assessment.support_level} />}
            </div>
          </div>
          {c.source_page && <p className="text-xs text-slate-400 mt-1">Page {c.source_page}</p>}
        </Link>
      ))}
    </div>
  );
}
