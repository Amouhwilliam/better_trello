import { Kanban } from "lucide-react";
import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import { DashboardClient } from "./DashboardClient";
import SignOutButton from "./SignOutButton";

const API_URL = process.env.API_URL ?? "http://api:8000";

function getUserIdFromToken(token: string): string | null {
  try {
    // base64url → base64: replace - with + and _ with /
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(Buffer.from(base64, "base64").toString("utf8"));
    return typeof payload.sub === "string" ? payload.sub : null;
  } catch {
    return null;
  }
}

async function getUser(userId: string, token: string) {
  const res = await fetch(`${API_URL}/users/${userId}`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch user");
  return res.json() as Promise<{ id: string; fullname: string; email: string }>;
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ userId?: string }>;
}) {
  const token = (await cookies()).get("bt_token")?.value;
  if (!token) redirect("/");

  const { userId: userIdParam } = await searchParams;

  // If userId not in URL, decode from token and redirect so URL is canonical
  if (!userIdParam) {
    const decoded = getUserIdFromToken(token);
    if (!decoded) redirect("/");
    redirect(`/dashboard?userId=${decoded}`);
  }

  const user = await getUser(userIdParam, token);
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
            <SignOutButton />
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 px-4 py-12">
        <div className="mx-auto w-full max-w-5xl">
          <div className="mb-10">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Hello, {firstName}! 👋
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Here&apos;s what&apos;s on your plate today.
            </p>
          </div>

          <DashboardClient userId={user.id} />
        </div>
      </main>
    </div>
  );
}
