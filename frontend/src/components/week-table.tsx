import { RELEVANCE_TONES } from "@/components/relevance-tones";
import type { PlacedCourse } from "@/lib/api/client";
import { RELEVANCE_LABELS, WEEKDAY_LABELS, classLabel } from "@/lib/labels";
import { weekTable } from "@/lib/timetable";

export function WeekTable({ courses }: { courses: PlacedCourse[] }) {
  const table = weekTable(courses);
  return (
    <div className="grid min-w-0 gap-2">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] table-fixed border-separate border-spacing-1.5 text-xs">
          <thead>
            <tr>
              <th className="w-6" />
              {table.weekdays.map((weekday) => (
                <th
                  key={weekday}
                  scope="col"
                  className="font-serif font-bold text-sub"
                >
                  {WEEKDAY_LABELS[weekday]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr key={row.period}>
                <th scope="row" className="font-serif font-bold text-sub">
                  {row.period}
                </th>
                {row.cells.map((cell, index) => (
                  <td
                    key={table.weekdays[index]}
                    className={`h-14 align-top ${cell.length === 0 ? "rounded-md border-[1.5px] border-dashed border-line" : ""}`}
                  >
                    {cell.map((course) => (
                      <span
                        key={course.section_code}
                        title={course.reason}
                        className={`mb-1 block rounded-sm px-2 py-1.5 leading-snug font-bold shadow-sticky [overflow-wrap:anywhere] last:mb-0 ${RELEVANCE_TONES[course.relevance].sticky}`}
                      >
                        {course.name}
                        <span className="mt-0.5 block text-[10.5px] font-medium text-sub">
                          {RELEVANCE_LABELS[course.relevance]}
                          {course.class_code !== null &&
                            ` ・ ${classLabel(course.class_code)}`}
                        </span>
                      </span>
                    ))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {table.unscheduled.length > 0 && (
        <p className="text-xs text-sub">
          コマの無い授業:{" "}
          {table.unscheduled.map((course) => course.name).join("、")}
        </p>
      )}
    </div>
  );
}
