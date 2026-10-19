import type { PlanStatus } from "@/lib/api/client";
import { STATUS_LABELS } from "@/lib/labels";

const STATUS_STYLES: Record<PlanStatus, string> = {
  pending: "border border-line text-sub",
  running: "bg-route-soft text-route",
  succeeded: "bg-route text-paper",
  failed: "bg-danger-soft text-danger",
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
