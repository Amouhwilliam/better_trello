import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Kanban, Clock } from "lucide-react";
import { cookies } from "next/headers";
import { BoardClient } from "./BoardClient";

const API_URL = process.env.API_URL ?? "http://api:8000";

async function getProject(id: string, token?: string) {
  const res = await fetch(`${API_URL}/projects/${id}`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch project");
  return res.json() as Promise<{
    id: string;
    title: string;
    deadline: string;
    completed: boolean;
    owner_id: string | null;
  }>;
}

export default async function ProjectBoardPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ userId?: string }>;
}) {
  const { id } = await params;
  const { userId = "" } = await searchParams;

  const token = (await cookies()).get("bt_token")?.value;
  const project = await getProject(id, token);
  if (!project) notFound();

  const deadline = new Date(project.deadline);

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-4 px-6">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Dashboard
          </Link>

          <div className="h-4 w-px bg-slate-200" />

          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
              <Kanban className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="font-semibold text-slate-800">{project.title}</span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400 ml-auto">
            <Clock className="h-3.5 w-3.5" />
            Due {deadline.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </div>
        </div>
      </header>

      {/* Board */}
      <main className="flex-1 overflow-x-auto p-8">
        <BoardClient
          projectId={id}
          userId={userId}
          projectTitle={project.title}
          projectDeadline={project.deadline}
        />
      </main>
    </div>
  );
}
