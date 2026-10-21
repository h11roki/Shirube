"use server";

import { signOut } from "@/auth";

export async function signOutToTop() {
  await signOut({ redirectTo: "/" });
}
