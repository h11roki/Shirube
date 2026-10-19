import { CourseCard } from "@/components/course-card";
import type { Course, PlacedCourse } from "@/lib/api/client";

export function CourseGrid({
  courses,
}: {
  courses: (Course | PlacedCourse)[];
}) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-[repeat(auto-fill,minmax(15rem,1fr))]">
      {courses.map((course) => (
        <CourseCard key={course.name} course={course} />
      ))}
    </div>
  );
}
