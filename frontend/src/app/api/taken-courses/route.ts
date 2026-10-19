import { forwardToBackend } from "@/lib/backend";

export async function GET(request: Request): Promise<Response> {
  return forwardToBackend("/taken-courses", request);
}
