import { forwardToBackend } from "@/lib/backend";

export async function GET(request: Request): Promise<Response> {
  const { search } = new URL(request.url);
  return forwardToBackend(`/class-choices${search}`, request);
}
