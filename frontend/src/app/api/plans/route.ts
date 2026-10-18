import { forwardToBackend } from "@/lib/backend";

export async function POST(request: Request): Promise<Response> {
  return forwardToBackend("/plans", request);
}
