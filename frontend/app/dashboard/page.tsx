import { LogOut, Kanban } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DashboardClient } from "./DashboardClient";

const API_URL = process.env.API_URL ?? "http://api:8000";

async function getUser(userId: string) {
  const res = await fetch(`${API_URL}/users/${userId}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch user");
  return res.json() as Promise<{ id: string; fullname: string; email: string }>;
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ userId?: string }>;
}) {
  const { userId } = await searchParams;
  if (!userId) notFound();

  const user = await getUser(userId);
  if (!user) notFound();

  const firstName = user.fullname.split(" ")[0];

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Navbar */}
      <header className="border-b border-slate-200 bg-white/70 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600">
              <Kanban className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-semibold text-slate-800">Better Trello</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
              {user.fullname
                .split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <Link
              href="/"
              className="flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </Link>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 px-4 py-12">
        <div className="mx-auto w-full max-w-5xl">
          {/* Greeting */}
          <div className="mb-10">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Hello, {firstName}! 👋
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Here&apos;s what&apos;s on your plate today.
            </p>
          </div>

          {/* Tabs + content */}
          <DashboardClient userId={user.id} />
        </div>
      </main>
    </div>
  );
}
