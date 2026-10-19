import { forwardToBackend } from "@/lib/backend";

type TakenCourseContext = RouteContext<"/api/plans/[id]/taken-courses/[name]">;

async function forward(
  request: Request,
  { params }: TakenCourseContext,
): Promise<Response> {
  const { id, name } = await params;
  return forwardToBackend(
    `/plans/${encodeURIComponent(id)}/taken-courses/${encodeURIComponent(name)}`,
    request,
  );
}

export const PUT = forward;
export const DELETE = forward;
