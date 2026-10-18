import { forwardToBackend } from "@/lib/backend";

export async function GET(
  request: Request,
  { params }: RouteContext<"/api/plans/[id]">,
): Promise<Response> {
  const { id } = await params;
  return forwardToBackend(`/plans/${encodeURIComponent(id)}`, request);
}
