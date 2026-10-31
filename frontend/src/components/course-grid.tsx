import { CourseTicket } from "@/components/course-ticket";
import type { Course, PlacedCourse } from "@/lib/api/client";
import type { Transfer } from "@/lib/roadmap";

export function CourseGrid({
  courses,
  transfers,
  serials,
}: {
  courses: (Course | PlacedCourse)[];
  transfers?: Map<string, Transfer>;
  serials?: Map<string, string>;
}) {
  return (
    <div
      data-ticket-grid
      className="grid gap-3 sm:grid-cols-[repeat(auto-fill,minmax(18rem,1fr))]"
    >
      {courses.map((course) => (
        <CourseTicket
          key={"section_code" in course ? course.section_code : course.name}
          course={course}
          transfer={transfers?.get(course.name)}
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
