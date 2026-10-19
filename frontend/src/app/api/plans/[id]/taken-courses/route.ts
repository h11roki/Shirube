import { forwardToBackend } from "@/lib/backend";

export async function PUT(
  request: Request,
  { params }: RouteContext<"/api/plans/[id]/taken-courses">,
): Promise<Response> {
  const { id } = await params;
  return forwardToBackend(
    `/plans/${encodeURIComponent(id)}/taken-courses`,
    request,
  );
}
