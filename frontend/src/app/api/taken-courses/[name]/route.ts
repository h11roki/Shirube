import { forwardToBackend } from "@/lib/backend";

export async function DELETE(
  request: Request,
  { params }: RouteContext<"/api/taken-courses/[name]">,
): Promise<Response> {
  const { name } = await params;
  return forwardToBackend(
    `/taken-courses/${encodeURIComponent(name)}`,
    request,
  );
}
