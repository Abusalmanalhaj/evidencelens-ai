const STATUS_COLORS: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  uploaded: "bg-slate-100 text-slate-700",
  ready: "bg-green-100 text-green-700",
  uploading: "bg-blue-100 text-blue-700",
  extracting: "bg-blue-100 text-blue-700",
  analyzing: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  strong: "bg-green-100 text-green-800",
  partial: "bg-yellow-100 text-yellow-800",
  weak: "bg-orange-100 text-orange-800",
  missing: "bg-red-100 text-red-800",
};

export default function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status.toLowerCase()] || "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}
