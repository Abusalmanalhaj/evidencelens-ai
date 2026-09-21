import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import type { Claim } from "../types";

const CATEGORIES = ["product", "technology", "scalability", "performance", "ip", "security", "market", "business", "other"];

export default function ClaimDetailPage() {
  const { id, claimId } = useParams<{ id: string; claimId: string }>();
  const projectId = Number(id);
  const cId = Number(claimId);
  const { token } = useAuth();
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [saving, setSaving] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);

  const refresh = async () => {
    if (!token) return;
    const c = await api.getClaim(token, projectId, cId);
    setClaim(c);
    setCategory(c.category);
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [token, projectId, cId]);

  const handleCategorySave = async () => {
    if (!token || !claim) return;
    setSaving(true);
    try {
      const updated = await api.updateClaimCategory(token, projectId, cId, category);
      setClaim(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleEvidenceToggle = async (evidenceId: number, isRelevant: boolean) => {
    if (!token) return;
    const updated = await api.updateEvidenceRelevance(token, projectId, cId, evidenceId, isRelevant);
    setClaim(updated);
  };

  if (loading) return <LoadingSpinner />;
  if (!claim) return <div>Claim not found</div>;

  return (
    <div>
      <Link to={`/projects/${projectId}`} className="text-sm text-brand-600 hover:underline">← Back to project</Link>

      <div className="mt-4 bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <h1 className="text-lg font-semibold text-slate-900">{claim.text}</h1>
          {claim.assessment && <StatusBadge status={claim.assessment.support_level} />}
        </div>
        {claim.source_page && (
          <p className="text-sm text-slate-500 mb-4">
            Original claim page: {claim.source_page}
            {claim.source_pages && claim.source_pages.length > 1 ? `; repeated on pages ${claim.source_pages.filter((page) => page !== claim.source_page).join(", ")}` : ""}
          </p>
        )}

        {claim.assessment && (
          <div className="bg-slate-50 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-4 mb-2">
              <span className="text-sm font-medium">Support Score: {(claim.assessment.support_score * 100).toFixed(0)}%</span>
              <span className="text-xs text-slate-500">
                Evidence: {claim.assessment.evidence_strength.toFixed(2)} |
                Traceability: {claim.assessment.source_traceability.toFixed(2)} |
                Relevance: {claim.assessment.evidence_relevance.toFixed(2)} |
                Sufficiency: {claim.assessment.evidence_sufficiency.toFixed(2)} |
                Specificity: {claim.assessment.specificity.toFixed(2)}
              </span>
            </div>
            <p className="text-xs text-slate-500 mb-2">
              Evidence pages: {claim.assessment.evidence_pages?.join(", ") || "none"} |
              Verification: {claim.assessment.verification_status.replace("_", " ")}
            </p>
            <p className="text-sm text-slate-600">{claim.assessment.explanation}</p>
          </div>
        )}

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-slate-700">Category:</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="border rounded-lg px-2 py-1 text-sm">
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          {category !== claim.category && (
            <button onClick={handleCategorySave} disabled={saving}
              className="text-sm bg-brand-600 text-white px-3 py-1 rounded-lg disabled:opacity-50">
              Save
            </button>
          )}
          {claim.ai_category && claim.human_category && claim.ai_category !== claim.human_category && (
            <span className="text-xs text-amber-600">AI: {claim.ai_category} → Human corrected</span>
          )}
        </div>
      </div>

      <h2 className="font-semibold mb-3">Evidence ({claim.evidence_items.length})</h2>
      <div className="space-y-3">
        {claim.evidence_items.map((ev) => (
          <div key={ev.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <button
              type="button"
              onClick={() => setExpandedEvidence(expandedEvidence === ev.id ? null : ev.id)}
              className="w-full flex items-center justify-between gap-4 p-4 text-left hover:bg-slate-50"
              aria-expanded={expandedEvidence === ev.id}
              aria-controls={`evidence-${ev.id}`}
            >
              <div className="min-w-0">
                <div className={`flex items-center gap-2 ${expandedEvidence === ev.id ? "" : "mb-1"}`}>
                  <span className="text-xs bg-slate-100 px-2 py-0.5 rounded capitalize">{ev.evidence_type}</span>
                  {ev.source_page && <span className="text-xs text-slate-400">Page {ev.source_page}</span>}
                  {ev.is_relevant === true && <span className="text-xs text-green-700">Marked relevant</span>}
                  {ev.is_relevant === false && <span className="text-xs text-red-700">Marked irrelevant</span>}
                </div>
                {expandedEvidence !== ev.id && (
                  <p className="text-sm text-slate-700 line-clamp-2">{ev.text}</p>
                )}
              </div>
              <span className="text-xs font-medium text-brand-600 shrink-0">
                {expandedEvidence === ev.id ? "Close evidence" : "Open evidence"}
              </span>
            </button>
            {expandedEvidence === ev.id && (
              <div id={`evidence-${ev.id}`} className="border-t border-slate-100 p-4 pt-3">
                <p className="text-sm text-slate-700 mb-3">{ev.text}</p>
                <div className="flex gap-1">
                  <button type="button" onClick={() => handleEvidenceToggle(ev.id, true)}
                  className={`text-xs px-2 py-1 rounded ${ev.is_relevant === true ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                  Relevant
                  </button>
                  <button type="button" onClick={() => handleEvidenceToggle(ev.id, false)}
                  className={`text-xs px-2 py-1 rounded ${ev.is_relevant === false ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500"}`}>
                  Irrelevant
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
