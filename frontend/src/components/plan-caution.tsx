import { TEXT_LINK } from "@/components/styles";
import { PLAN_CAUTION, SYLLABUS_SITE, sourceNote } from "@/lib/labels";

export function PlanCaution() {
  return (
    <p
      role="note"
      className="max-w-2xl rounded-md border border-line bg-sheet px-3.5 py-2.5 text-[13px] leading-relaxed text-sub"
    >
      {PLAN_CAUTION}
    </p>
  );
}

export function SourceNote({ year }: { year: number }) {
  return (
    <p className="text-xs leading-relaxed text-sub">
      {sourceNote(year)}
      <a
        href={SYLLABUS_SITE}
        target="_blank"
        rel="noopener noreferrer"
        className={`ml-1 ${TEXT_LINK}`}
      >
        立命館大学 シラバス
        <span aria-hidden> ↗</span>
      </a>
    </p>
  );
}
