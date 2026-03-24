"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Kanban, Plus, X, Loader2, Users, FolderKanban, CheckCircle2, Clock, Eye, EyeOff, ListTodo, Calendar, UserPlus, AlertCircle, Pencil, Search, Link2Off } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { api, type Project, type Task, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import SignOutButton from "./SignOutButton";

// ─── Schemas ─────────────────────────────────────────────────────────────────

const projectSchema = z.object({
  title: z.string().min(2, "Title must be at least 2 characters."),
  deadline: z.string().min(1, "Deadline is required."),
});
type ProjectForm = z.infer<typeof projectSchema>;

const userSchema = z.object({
  fullname: z.string().min(2, "Full name must be at least 2 characters."),
  email: z.email("Please enter a valid email address."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});
type UserForm = z.infer<typeof userSchema>;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ACCENT = ["indigo", "violet", "sky", "emerald", "rose", "amber"] as const;
const accent = (i: number) => ACCENT[i % ACCENT.length];
type Tab = "projects" | "contributors" | "tasks";

// ─── Main component ───────────────────────────────────────────────────────────

export function DashboardClient() {
  const [tab, setTab] = useState<Tab>("projects");
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [showContributorPassword, setShowContributorPassword] = useState(false);
  const queryClient = useQueryClient();

  const { data: currentUser } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.users.me(),
  });

  const userId = currentUser?.id ?? "";

  const { data: projects = [], isLoading: loadingProjects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(),
  });

  const { data: users = [], isLoading: loadingUsers } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.users.list(),
    enabled: tab === "contributors" || tab === "tasks",
  });

  const { data: allTasks = [], isLoading: loadingTasks } = useQuery({
    queryKey: ["all-tasks"],
    queryFn: () => api.tasks.list(),
    enabled: tab === "tasks",
  });

  const [editingTaskProject, setEditingTaskProject] = useState<Task | null>(null);
  const [taskPage, setTaskPage] = useState(1);
  const TASKS_PER_PAGE = 15;

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

  const firstName = currentUser?.fullname.split(" ")[0] ?? "";
  const initials = currentUser?.fullname
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() ?? "";

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
            {initials && (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
                {initials}
              </div>
            )}
            <SignOutButton />
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 px-4 py-12">
        <div className="mx-auto w-full max-w-5xl">
          <div className="mb-10">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              {firstName ? `Hello, ${firstName}! 👋` : "Welcome!"}
            </h1>
            <p className="mt-2 text-sm text-slate-500">Here&apos;s what&apos;s on your plate today.</p>
          </div>

      {/* Tabs */}
      <div className="mb-8 flex items-center gap-1 border-b border-slate-200">
        {(["projects", "contributors", "tasks"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "projects" ? <FolderKanban className="h-4 w-4" /> : t === "contributors" ? <Users className="h-4 w-4" /> : <ListTodo className="h-4 w-4" />}
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

      {/* Tasks tab */}
      {tab === "tasks" && (() => {
        const totalPages = Math.max(1, Math.ceil(allTasks.length / TASKS_PER_PAGE));
        const pageTasks = allTasks.slice((taskPage - 1) * TASKS_PER_PAGE, taskPage * TASKS_PER_PAGE);
        return (
          <>
            <div className="mb-6 flex items-center justify-between">
              <p className="text-sm text-slate-500">
                {allTasks.length === 0
                  ? "No tasks yet."
                  : `${allTasks.length} task${allTasks.length > 1 ? "s" : ""} across all projects`}
              </p>
            </div>

            {loadingTasks ? (
              <div className="flex justify-center py-16">
                <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
              </div>
            ) : allTasks.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/50 py-16 text-slate-400">
                <ListTodo className="mb-3 h-10 w-10 opacity-30" />
                <p className="text-sm">No tasks found on the platform.</p>
              </div>
            ) : (
              <>
                <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Title</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Due date</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Assignee</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Project</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {pageTasks.map((task) => (
                        <TaskRow
                          key={task.id}
                          task={task}
                          assignee={task.assignee_id ? users.find((u) => u.id === task.assignee_id) : undefined}
                          project={task.project_id ? projects.find((p) => p.id === task.project_id) : undefined}
                          onEditProject={() => setEditingTaskProject(task)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-xs text-slate-400">
                      Showing {(taskPage - 1) * TASKS_PER_PAGE + 1}–{Math.min(taskPage * TASKS_PER_PAGE, allTasks.length)} of {allTasks.length}
                    </p>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setTaskPage((p) => Math.max(1, p - 1))}
                        disabled={taskPage === 1}
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition-colors hover:border-indigo-300 hover:text-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        ‹
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                        <button
                          key={p}
                          onClick={() => setTaskPage(p)}
                          className={`flex h-8 w-8 items-center justify-center rounded-lg border text-xs font-medium transition-colors ${
                            p === taskPage
                              ? "border-indigo-600 bg-indigo-600 text-white"
                              : "border-slate-200 bg-white text-slate-600 hover:border-indigo-300 hover:text-indigo-600"
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                      <button
                        onClick={() => setTaskPage((p) => Math.min(totalPages, p + 1))}
                        disabled={taskPage === totalPages}
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 transition-colors hover:border-indigo-300 hover:text-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        ›
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        );
      })()}

      {/* Task project edit modal */}
      {editingTaskProject && (
        <TaskProjectModal
          task={editingTaskProject}
          projects={projects}
          onDone={() => {
            setEditingTaskProject(null);
            queryClient.invalidateQueries({ queryKey: ["all-tasks"] });
          }}
          onClose={() => setEditingTaskProject(null)}
        />
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
              <div className="relative">
                <Input
                  id="u-password"
                  type={showContributorPassword ? "text" : "password"}
                  placeholder="••••••••"
                  className="h-11 pr-10"
                  {...regUser("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowContributorPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  {showContributorPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
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

        </div>
      </main>
    </div>
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

function TaskRow({
  task,
  assignee,
  project,
  onEditProject,
}: {
  task: Task;
  assignee?: User;
  project?: Project;
  onEditProject: () => void;
}) {
  const [hoveringProject, setHoveringProject] = useState(false);
  const deadline = new Date(task.deadline);
  const now = new Date();
  const isOverdue = !task.completed && deadline < now;

  const statusColors: Record<string, string> = {
    todo: "bg-slate-100 text-slate-600",
    in_progress: "bg-blue-50 text-blue-700",
    completed: "bg-emerald-50 text-emerald-700",
  };
  const statusLabels: Record<string, string> = {
    todo: "To Do",
    in_progress: "In Progress",
    completed: "Completed",
  };

  return (
    <tr className="transition-colors hover:bg-slate-50">
      <td className="px-4 py-3 font-medium text-slate-800">{task.title}</td>
      <td className="px-4 py-3">
        <span className={`flex items-center gap-1 text-xs ${isOverdue ? "text-red-500 font-medium" : "text-slate-500"}`}>
          {isOverdue && <AlertCircle className="h-3 w-3 shrink-0" />}
          <Calendar className="h-3 w-3 shrink-0" />
          {deadline.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
        </span>
      </td>
      <td className="px-4 py-3">
        {assignee ? (
          <span className="flex items-center gap-1.5">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[9px] font-bold text-indigo-700">
              {assignee.fullname.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
            </span>
            <span className="text-xs text-slate-700">{assignee.fullname}</span>
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-slate-300">
            <UserPlus className="h-3 w-3" />
            Unassigned
          </span>
        )}
      </td>
      <td
        className="px-4 py-3"
        onMouseEnter={() => setHoveringProject(true)}
        onMouseLeave={() => setHoveringProject(false)}
      >
        <span className="flex items-center gap-1.5">
          {project ? (
            <Link
              href={`/projects/${project.id}`}
              className="text-xs font-medium text-indigo-600 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {project.title}
            </Link>
          ) : (
            <span className="text-xs text-slate-300">—</span>
          )}
          <button
            onClick={onEditProject}
            className={`flex h-5 w-5 items-center justify-center rounded transition-opacity ${
              hoveringProject ? "opacity-100" : "opacity-0"
            } text-slate-400 hover:text-indigo-600 hover:bg-indigo-50`}
          >
            <Pencil className="h-3 w-3" />
          </button>
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[task.status] ?? statusColors.todo}`}>
          {statusLabels[task.status] ?? task.status}
        </span>
      </td>
    </tr>
  );
}

// ─── Task project modal ───────────────────────────────────────────────────────

function TaskProjectModal({
  task,
  projects,
  onDone,
  onClose,
}: {
  task: Task;
  projects: Project[];
  onDone: () => void;
  onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Project | null>(
    projects.find((p) => p.id === task.project_id) ?? null
  );

  const { mutate: save, isPending } = useMutation({
    mutationFn: async () => {
      if (selected?.id === task.project_id) return; // nothing changed
      if (task.project_id && !selected) {
        // unlink
        await api.tasks.unlinkProject(task.id, task.project_id);
      } else if (selected) {
        // link (will replace existing via backend logic)
        await api.tasks.linkProject(task.id, selected.id);
      }
    },
    onSuccess: () => {
      toast.success("Task project updated.");
      onDone();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const filtered = projects.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Edit project</h2>
            <p className="mt-0.5 text-xs text-slate-400 truncate max-w-[220px]">
              Task: <span className="font-medium text-slate-600">{task.title}</span>
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <Input
              autoFocus
              placeholder="Search projects…"
              className="h-9 pl-8 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Project list */}
          <div className="max-h-52 overflow-y-auto rounded-xl border border-slate-100 divide-y divide-slate-50">
            {/* None option */}
            <button
              type="button"
              onClick={() => setSelected(null)}
              className={`flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors ${
                selected === null ? "bg-indigo-50 text-indigo-700 font-medium" : "text-slate-400 hover:bg-slate-50"
              }`}
            >
              <Link2Off className="h-3.5 w-3.5 shrink-0" />
              No project
            </button>

            {filtered.length === 0 && (
              <p className="py-4 text-center text-xs text-slate-400">No projects match.</p>
            )}

            {filtered.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelected(p)}
                className={`flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm transition-colors ${
                  selected?.id === p.id ? "bg-indigo-50 text-indigo-700 font-medium" : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <span className="truncate">{p.title}</span>
                {selected?.id === p.id && (
                  <span className="shrink-0 text-xs text-indigo-400">selected</span>
                )}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <Button type="button" variant="outline" className="flex-1 h-9" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={isPending || selected?.id === task.project_id}
              onClick={() => save()}
              className="flex-1 h-9 bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40"
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
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
