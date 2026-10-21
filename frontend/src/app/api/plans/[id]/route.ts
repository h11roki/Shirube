import { forwardToBackend } from "@/lib/backend";

async function forward(
  request: Request,
  { params }: RouteContext<"/api/plans/[id]">,
): Promise<Response> {
  const { id } = await params;
  return forwardToBackend(`/plans/${encodeURIComponent(id)}`, request);
}

export const GET = forward;
export const DELETE = forward;
