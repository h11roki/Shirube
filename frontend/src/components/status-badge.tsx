import type { PlanStatus } from "@/lib/api/client";
import { STATUS_LABELS } from "@/lib/labels";

const STATUS_STYLES: Record<PlanStatus, string> = {
  pending: "text-sub",
  running: "text-route",
  succeeded: "text-ink",
  failed: "text-danger",
};

export function StatusBadge({ status }: { status: PlanStatus }) {
  return (
    <span className={`inline-block text-xs font-bold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}
