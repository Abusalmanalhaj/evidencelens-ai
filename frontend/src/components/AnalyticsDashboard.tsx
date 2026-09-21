import { useEffect, useState } from "react";
import {
  Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api/client";
import LoadingSpinner from "./LoadingSpinner";
import { useAuth } from "../context/AuthContext";
import type { DashboardMetrics } from "../types";

const SUPPORT_COLORS = ["#22c55e", "#eab308", "#f97316", "#ef4444"];

export default function AnalyticsDashboard({ projectId }: { projectId: number }) {
  const { token } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api.getDashboard(token, projectId)
      .then(setMetrics)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, projectId]);

  if (loading) return <LoadingSpinner message="Loading analytics..." />;
  if (error) return <div className="text-red-600 text-sm">{error}</div>;
  if (!metrics) return null;

  const supportData = [
    { name: "Strong", value: metrics.support_breakdown.strong },
    { name: "Partial", value: metrics.support_breakdown.partial },
    { name: "Weak", value: metrics.support_breakdown.weak },
    { name: "Missing", value: metrics.support_breakdown.missing },
  ].filter((d) => d.value > 0);

  const categoryData = metrics.category_breakdown.map((c) => ({
    name: c.category,
    count: c.count,
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Claims" value={metrics.total_claims} />
        <StatCard label="Evidence Coverage" value={`${metrics.evidence_coverage}%`} />
        <StatCard label="Needs Review" value={metrics.requires_review_count} />
        <StatCard label="Status" value={metrics.analysis_status} />
      </div>

      {metrics.total_claims === 0 ? (
        <div className="text-center py-12 text-slate-500 bg-white rounded-xl border">
          No analysis data yet. Upload a pitch deck and run analysis to see metrics.
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold mb-4">Evidence Support Breakdown</h3>
            {supportData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={supportData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                    {supportData.map((_, i) => (
                      <Cell key={i} fill={SUPPORT_COLORS[i % SUPPORT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-500">No support data</p>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold mb-4">Claims by Category</h3>
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={categoryData}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-500">No category data</p>
            )}
          </div>
        </div>
      )}

      <p className="text-xs text-slate-400 text-center">
        Scores reflect evidence support from the pitch deck, not verified factual truth.
      </p>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-slate-900 mt-1 capitalize">{value}</p>
    </div>
  );
}
