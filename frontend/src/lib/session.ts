import { connection } from "next/server";
import { cache } from "react";

import { auth } from "@/auth";

export const currentSession = cache(async () => {
  await connection();
  return auth();
});
