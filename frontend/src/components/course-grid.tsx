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
      {courses.map((course) => (
        <CourseTicket
          key={"section_code" in course ? course.section_code : course.name}
          course={course}
          transfer={routes?.departures.get(course.name)}
          arrivals={routes?.arrivals.get(course.name)}
          serial={
            "section_code" in course
              ? serials?.get(course.section_code)
              : undefined
          }
        />
      ))}
    </div>
  );
}
