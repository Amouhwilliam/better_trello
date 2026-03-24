"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Kanban, Plus, X, Loader2, Users, FolderKanban, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { api, type Project, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

// ─── Schemas ─────────────────────────────────────────────────────────────────

const projectSchema = z.object({
  title: z.string().min(2, "Title must be at least 2 characters."),
  deadline: z.string().min(1, "Deadline is required."),
});
type ProjectForm = z.infer<typeof projectSchema>;

const userSchema = z.object({
  fullname: z.string().min(2, "Full name must be at least 2 characters."),
  email: z.string().email("Please enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});
type UserForm = z.infer<typeof userSchema>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ACCENT = ["indigo", "violet", "sky", "emerald", "rose", "amber"] as const;
const accent = (i: number) => ACCENT[i % ACCENT.length];
type Tab = "projects" | "contributors";

// ─── Main component ───────────────────────────────────────────────────────────

export function DashboardClient({ userId }: { userId: string }) {
  const [tab, setTab] = useState<Tab>("projects");
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: projects = [], isLoading: loadingProjects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(),
  });

  const { data: users = [], isLoading: loadingUsers } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.users.list(),
    enabled: tab === "contributors",
  });

  // ── Project form ──
  const {
    register: regProject,
    handleSubmit: submitProject,
    reset: resetProject,
    formState: { errors: projectErrors },
    setError: setProjectError,
  } = useForm<ProjectForm>({ resolver: zodResolver(projectSchema) });

  const { mutate: createProject, isPending: creatingProject } = useMutation({
    mutationFn: (v: ProjectForm) =>
      api.projects.create({
        title: v.title,
        deadline: new Date(v.deadline).toISOString(),
        owner_id: userId,
      }),
    onSuccess: (p) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setProjectModalOpen(false);
      resetProject();
      toast.success(`Project "${p.title}" created.`);
    },
    onError: (err: Error) => {
      setProjectError("root", { message: err.message });
      toast.error(err.message);
    },
  });

  // ── User form ──
  const {
    register: regUser,
    handleSubmit: submitUser,
    reset: resetUser,
    formState: { errors: userErrors },
    setError: setUserError,
  } = useForm<UserForm>({ resolver: zodResolver(userSchema) });

  const { mutate: createUser, isPending: creatingUser } = useMutation({
    mutationFn: (v: UserForm) =>
      api.users.create({ fullname: v.fullname, email: v.email, password: v.password }),
    onSuccess: (u) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setUserModalOpen(false);
      resetUser();
      toast.success(`${u.fullname} added as a contributor.`);
    },
    onError: (err: Error) => {
      setUserError("root", { message: err.message });
      toast.error(err.message);
    },
  });

  return (
    <>
      {/* Tabs */}
      <div className="mb-8 flex items-center gap-1 border-b border-slate-200">
        {(["projects", "contributors"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "projects" ? <FolderKanban className="h-4 w-4" /> : <Users className="h-4 w-4" />}
            {t}
          </button>
        ))}
      </div>

      {/* Projects tab */}
      {tab === "projects" && (
        <>
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm text-slate-500">
              {projects.length === 0 ? "No projects yet." : `${projects.length} project${projects.length > 1 ? "s" : ""}`}
            </p>
            <Button onClick={() => setProjectModalOpen(true)} className="h-9 gap-2 bg-indigo-600 text-white hover:bg-indigo-700">
              <Plus className="h-4 w-4" />
              New project
            </Button>
          </div>

          {loadingProjects ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
            </div>
          ) : projects.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/50 py-16 text-slate-400">
              <FolderKanban className="mb-3 h-10 w-10 opacity-30" />
              <p className="text-sm">Create your first project to get started.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((p, i) => (
                <ProjectCard key={p.id} project={p} colorIndex={i} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Contributors tab */}
      {tab === "contributors" && (
        <>
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm text-slate-500">
              {users.length === 0 ? "No contributors yet." : `${users.length} contributor${users.length > 1 ? "s" : ""}`}
            </p>
            <Button onClick={() => setUserModalOpen(true)} className="h-9 gap-2 bg-indigo-600 text-white hover:bg-indigo-700">
              <Plus className="h-4 w-4" />
              New contributor
            </Button>
          </div>

          {loadingUsers ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
            </div>
          ) : users.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/50 py-16 text-slate-400">
              <Users className="mb-3 h-10 w-10 opacity-30" />
              <p className="text-sm">No contributors yet. Add the first one.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {users.map((u) => (
                <UserCard key={u.id} user={u} isCurrentUser={u.id === userId} />
              ))}
            </div>
          )}
        </>
      )}

      {/* New project modal */}
      {projectModalOpen && (
        <Modal onClose={() => { setProjectModalOpen(false); resetProject(); }}>
          <ModalHeader
            title="New project"
            subtitle="Fill in the details to get started."
            onClose={() => { setProjectModalOpen(false); resetProject(); }}
          />
          <form onSubmit={submitProject((v) => createProject(v))} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="p-title" className="text-sm font-medium text-slate-700">Project title</Label>
              <Input id="p-title" placeholder="e.g. Q2 Roadmap" autoFocus className="h-11" {...regProject("title")} />
              {projectErrors.title && <p className="text-xs text-red-500">{projectErrors.title.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="p-deadline" className="text-sm font-medium text-slate-700">Deadline</Label>
              <Input id="p-deadline" type="datetime-local" className="h-11" {...regProject("deadline")} />
              {projectErrors.deadline && <p className="text-xs text-red-500">{projectErrors.deadline.message}</p>}
            </div>
            {projectErrors.root && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{projectErrors.root.message}</p>
            )}
            <ModalActions
              onCancel={() => { setProjectModalOpen(false); resetProject(); }}
              isPending={creatingProject}
              label="Create project"
            />
          </form>
        </Modal>
      )}

      {/* New contributor modal */}
      {userModalOpen && (
        <Modal onClose={() => { setUserModalOpen(false); resetUser(); }}>
          <ModalHeader
            title="New contributor"
            subtitle="Add a team member to your workspace."
            onClose={() => { setUserModalOpen(false); resetUser(); }}
          />
          <form onSubmit={submitUser((v) => createUser(v))} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="u-fullname" className="text-sm font-medium text-slate-700">Full name</Label>
              <Input id="u-fullname" placeholder="Alice Dupont" autoFocus className="h-11" {...regUser("fullname")} />
              {userErrors.fullname && <p className="text-xs text-red-500">{userErrors.fullname.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="u-email" className="text-sm font-medium text-slate-700">Email address</Label>
              <Input id="u-email" type="email" placeholder="alice@example.com" className="h-11" {...regUser("email")} />
              {userErrors.email && <p className="text-xs text-red-500">{userErrors.email.message}</p>}
            </div>
            <Separator />
            <div className="space-y-1.5">
              <Label htmlFor="u-password" className="text-sm font-medium text-slate-700">Password</Label>
              <Input id="u-password" type="password" placeholder="••••••••" className="h-11" {...regUser("password")} />
              {userErrors.password && <p className="text-xs text-red-500">{userErrors.password.message}</p>}
            </div>
            {userErrors.root && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{userErrors.root.message}</p>
            )}
            <ModalActions
              onCancel={() => { setUserModalOpen(false); resetUser(); }}
              isPending={creatingUser}
              label="Add contributor"
            />
          </form>
        </Modal>
      )}
    </>
  );
}

// ─── Shared modal primitives ──────────────────────────────────────────────────

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function ModalHeader({ title, subtitle, onClose }: { title: string; subtitle: string; onClose: () => void }) {
  return (
    <div className="mb-6 flex items-center justify-between">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>
      </div>
      <button
        onClick={onClose}
        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

function ModalActions({ onCancel, isPending, label }: { onCancel: () => void; isPending: boolean; label: string }) {
  return (
    <div className="flex gap-3 pt-2">
      <Button type="button" variant="outline" className="flex-1 h-11" onClick={onCancel}>
        Cancel
      </Button>
      <Button type="submit" disabled={isPending} className="flex-1 h-11 bg-indigo-600 text-white hover:bg-indigo-700">
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : label}
      </Button>
    </div>
  );
}

// ─── Cards ────────────────────────────────────────────────────────────────────

function ProjectCard({ project, colorIndex }: { project: Project; colorIndex: number }) {
  const c = accent(colorIndex);
  const deadline = new Date(project.deadline);
  const isOverdue = !project.completed && deadline < new Date();

  const bgMap: Record<string, string> = {
    indigo: "bg-indigo-100", violet: "bg-violet-100", sky: "bg-sky-100",
    emerald: "bg-emerald-100", rose: "bg-rose-100", amber: "bg-amber-100",
  };
  const textMap: Record<string, string> = {
    indigo: "text-indigo-600", violet: "text-violet-600", sky: "text-sky-600",
    emerald: "text-emerald-600", rose: "text-rose-600", amber: "text-amber-600",
  };

  return (
    <Link
      href={`/projects/${project.id}`}
      className="group block rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-100 transition-all hover:shadow-md hover:border-indigo-200"
    >
      <div className="mb-4 flex items-start justify-between">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${bgMap[c]}`}>
          <Kanban className={`h-5 w-5 ${textMap[c]}`} />
        </div>
        {project.completed && (
          <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">
            <CheckCircle2 className="h-3 w-3" /> Done
          </span>
        )}
      </div>
      <h3 className="font-semibold text-slate-800 group-hover:text-indigo-700 transition-colors">{project.title}</h3>
      <p className={`mt-1 flex items-center gap-1 text-xs ${isOverdue ? "text-red-500" : "text-slate-400"}`}>
        <Clock className="h-3 w-3" />
        {isOverdue ? "Overdue · " : "Due "}
        {deadline.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
      </p>
    </Link>
  );
}

function UserCard({ user, isCurrentUser }: { user: User; isCurrentUser: boolean }) {
  const initials = user.fullname
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm shadow-slate-100">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700">
        {initials}
      </div>
      <div className="min-w-0">
        <p className="truncate font-medium text-slate-800">
          {user.fullname}
          {isCurrentUser && (
            <span className="ml-2 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-normal text-indigo-500">you</span>
          )}
        </p>
        <p className="truncate text-xs text-slate-400">{user.email}</p>
      </div>
    </div>
  );
}
