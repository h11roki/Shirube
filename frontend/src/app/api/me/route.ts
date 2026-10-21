import { forwardToBackend } from "@/lib/backend";

export async function DELETE(request: Request): Promise<Response> {
  return forwardToBackend("/me", request);
}
