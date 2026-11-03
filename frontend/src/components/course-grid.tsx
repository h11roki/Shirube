import { CourseTicket } from "@/components/course-ticket";
import type { Course, PlacedCourse } from "@/lib/api/client";
import type { TransferRoutes } from "@/lib/roadmap";

export function CourseGrid({
  courses,
  routes,
  serials,
}: {
  courses: (Course | PlacedCourse)[];
  routes?: TransferRoutes;
  serials?: Map<string, string>;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-[repeat(auto-fill,minmax(18rem,1fr))]">
      {courses.map((course) => {
        const section = "section_code" in course ? course.section_code : null;
        const transfer = routes?.departures.get(course.name);
        const arrivals = routes?.arrivals.get(course.name);
        return (
          <CourseTicket
            key={section ?? course.name}
            course={course}
            transfer={transfer?.from.section === section ? transfer : undefined}
            arrivals={
              arrivals?.[0].to.section === section ? arrivals : undefined
            }
            serial={section === null ? undefined : serials?.get(section)}
          />
        );
      })}
    </div>
  );
}
