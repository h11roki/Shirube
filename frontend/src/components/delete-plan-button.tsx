"use client";

import { useRouter } from "next/navigation";

import { ConfirmButton } from "@/components/confirm-button";
import { deletePlan } from "@/lib/api/client";
import {
  CONFIRM_DELETE_LABEL,
  DELETE_PLAN_LABEL,
  DELETE_PLAN_NOTE,
} from "@/lib/labels";

export function DeletePlanButton({
  id,
  onDeleting,
}: {
  id: string;
  onDeleting?: (deleting: boolean) => void;
}) {
  const router = useRouter();
  return (
    <ConfirmButton
      label={DELETE_PLAN_LABEL}
      note={DELETE_PLAN_NOTE}
      confirmLabel={CONFIRM_DELETE_LABEL}
      onConfirm={async () => {
        onDeleting?.(true);
        await deletePlan(id).catch((error: unknown) => {
          onDeleting?.(false);
          throw error;
        });
        router.replace("/plans");
      }}
    />
  );
}
