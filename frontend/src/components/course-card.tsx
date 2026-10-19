import type { Course, PlacedCourse } from "@/lib/api/client";
import { placementLabel, roleLabel } from "@/lib/labels";

export function CourseCard({ course }: { course: Course | PlacedCourse }) {
  const core = course.relevance === "core";
  return (
    <article
      className={`grid min-w-0 content-start gap-1 rounded-sm border border-l-4 border-line bg-sheet px-3.5 py-3 shadow-paper ${core ? "border-l-pillar" : "border-l-route"}`}
    >
      <p
        className={`text-[11px] font-bold tracking-[0.14em] ${core ? "text-pillar" : "text-route"}`}
      >
        {roleLabel(course)}
      </p>
      <h3 className="leading-snug font-bold">{course.name}</h3>
      <p className="text-[13px] leading-relaxed text-sub">{course.reason}</p>
      {"slots" in course && (
        <p className="text-xs text-sub tabular-nums">
          {placementLabel(course)}
          {!course.class_confirmed && (
            <span className="text-pillar"> ・ クラス未確定</span>
          )}
        </p>
      )}
    </article>
  );
}
