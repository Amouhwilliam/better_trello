"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

export default function SignOutButton() {
  const router = useRouter();

  async function signOut() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/");
  }

  return (
    <button
      onClick={signOut}
      className="flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600"
    >
      <LogOut className="h-3.5 w-3.5" />
      Sign out
    </button>
  );
}
