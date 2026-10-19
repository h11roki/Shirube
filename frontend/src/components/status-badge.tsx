import type { PlanStatus } from "@/lib/api/client";
import { STATUS_LABELS } from "@/lib/labels";

const STATUS_STYLES: Record<PlanStatus, string> = {
  pending: "bg-stone-100 text-stone-700",
  running: "bg-sky-100 text-sky-800",
  succeeded: "bg-teal-100 text-teal-800",
  failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: PlanStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
