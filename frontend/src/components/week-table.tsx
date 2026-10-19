import type { PlacedCourse, Relevance } from "@/lib/api/client";
import { WEEKDAY_LABELS } from "@/lib/labels";
import { weekTable } from "@/lib/timetable";

const RELEVANCE_STYLES: Record<Relevance, string> = {
  core: "bg-teal-50 text-teal-900 ring-teal-200",
  foundation: "bg-amber-50 text-amber-900 ring-amber-200",
};

export function WeekTable({ courses }: { courses: PlacedCourse[] }) {
  const table = weekTable(courses);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] table-fixed border-collapse text-xs">
        <thead>
          <tr>
            <th className="w-10" />
            {table.weekdays.map((weekday) => (
              <th
                key={weekday}
                scope="col"
                className="pb-1 font-medium text-stone-500"
              >
                {WEEKDAY_LABELS[weekday]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.period}>
              <th
                scope="row"
                className="pr-2 text-right font-medium text-stone-500"
              >
                {row.period}
              </th>
              {row.cells.map((cell, index) => (
                <td
                  key={table.weekdays[index]}
                  className="h-12 border border-stone-200 p-1 align-top"
                >
                  {cell.map((course) => (
                    <span
                      key={course.section_code}
                      className={`mb-1 block truncate rounded px-1.5 py-1 ring-1 ${RELEVANCE_STYLES[course.relevance]}`}
                      title={course.name}
                    >
                      {course.name}
                    </span>
                  ))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.unscheduled.length > 0 && (
        <p className="mt-2 text-xs text-stone-500">
          コマの無い授業:{" "}
          {table.unscheduled.map((course) => course.name).join("、")}
        </p>
      )}
    </div>
  );
}
