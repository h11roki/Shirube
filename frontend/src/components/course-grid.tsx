import { CourseTicket } from "@/components/course-ticket";
import type { Course, PlacedCourse } from "@/lib/api/client";
import type { Transfer } from "@/lib/roadmap";

export function CourseGrid({
  courses,
  transfers,
}: {
  courses: (Course | PlacedCourse)[];
  transfers?: Map<string, Transfer>;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-[repeat(auto-fill,minmax(18rem,1fr))]">
      {courses.map((course) => (
        <CourseTicket
          key={"section_code" in course ? course.section_code : course.name}
          course={course}
          transfer={transfers?.get(course.name)}
        />
      ))}
    </div>
  );
}
