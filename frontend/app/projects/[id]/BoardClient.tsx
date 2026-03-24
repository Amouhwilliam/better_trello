"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Plus, X, Loader2, UserPlus, Search, Calendar, AlertCircle, ChevronDown, Pencil, CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { api, type Task, type TaskStatus, type User } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// ─── Constants ────────────────────────────────────────────────────────────────

type Column = { id: TaskStatus; label: string; dropColor: string; headerClass: string };

const COLUMNS: Column[] = [
  { id: "todo",        label: "To Do",       dropColor: "bg-slate-50",   headerClass: "bg-slate-100 text-slate-600"     },
  { id: "in_progress", label: "In Progress", dropColor: "bg-blue-50",    headerClass: "bg-blue-100 text-blue-700"       },
  { id: "completed",   label: "Completed",   dropColor: "bg-emerald-50", headerClass: "bg-emerald-100 text-emerald-700" },
];

const STATUS_LABEL: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  completed: "Completed",
};

// ─── Schema ───────────────────────────────────────────────────────────────────

const taskSchema = z.object({
  title: z.string().min(1, "Title is required."),
  deadline: z.string().min(1, "Deadline is required."),
  description: z.string().optional(),
});
type TaskForm = z.infer<typeof taskSchema>;

// ─── Board ────────────────────────────────────────────────────────────────────

export function BoardClient({
  projectId,
  projectTitle: initialTitle,
  projectDeadline: initialDeadline,
  projectCompleted: initialCompleted,
  projectAutoComplete: initialAutoComplete,
}: {
  projectId: string;
  userId: string;
  projectTitle: string;
  projectDeadline: string;
  projectCompleted: boolean;
  projectAutoComplete: boolean;
}) {
  const queryClient = useQueryClient();
  const [createForStatus, setCreateForStatus] = useState<TaskStatus | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [editingProject, setEditingProject] = useState(false);
  const [projectTitle, setProjectTitle] = useState(initialTitle);
  const [projectDeadline, setProjectDeadline] = useState(initialDeadline);
  const [projectCompleted, setProjectCompleted] = useState(initialCompleted);
  const [projectAutoComplete, setProjectAutoComplete] = useState(initialAutoComplete);

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["project-tasks", projectId],
    queryFn: () => api.projects.tasks(projectId),
    refetchOnMount: "always",
  });

  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.users.list(),
  });

  const usersById = Object.fromEntries(users.map((u) => [u.id, u]));

  const { mutate: moveTask } = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: TaskStatus }) =>
      api.tasks.updateStatus(taskId, status),
    onMutate: async ({ taskId, status }) => {
      await queryClient.cancelQueries({ queryKey: ["project-tasks", projectId] });
      const prev = queryClient.getQueryData<Task[]>(["project-tasks", projectId]);
      queryClient.setQueryData<Task[]>(["project-tasks", projectId], (old = []) =>
        old.map((t) => (t.id === taskId ? { ...t, status, completed: status === "completed" } : t))
      );
      return { prev };
    },
    onSuccess: (_data, { status }) => toast.success(`Task moved to ${STATUS_LABEL[status]}.`),
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["project-tasks", projectId], ctx.prev);
      toast.error("Failed to move task. Please try again.");
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] }),
  });

  const onDragEnd = useCallback(
    (result: DropResult) => {
      if (!result.destination) return;
      const newStatus = result.destination.droppableId as TaskStatus;
      const taskId = result.draggableId;
      const task = tasks.find((t) => t.id === taskId);
      if (!task || task.status === newStatus) return;
      moveTask({ taskId, status: newStatus });
    },
    [tasks, moveTask]
  );

  const tasksByStatus = (status: TaskStatus) => tasks.filter((t) => t.status === status);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
      </div>
    );
  }

  return (
    <>
      {/* Project edit button */}
      <div className="mb-6 flex justify-end max-w-screen-xl mx-auto">
        <button
          onClick={() => setEditingProject(true)}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500 shadow-sm transition-colors hover:border-indigo-300 hover:text-indigo-600"
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit project
        </button>
      </div>

      <DragDropContext onDragEnd={onDragEnd}>
        <div className="flex justify-center">
          <div className="flex gap-5">
            {COLUMNS.map((col) => (
              <div key={col.id} className="flex w-72 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className={`flex items-center justify-between rounded-t-2xl px-4 py-3 ${col.headerClass}`}>
                  <span className="text-sm font-semibold">{col.label}</span>
                  <span className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-semibold tabular-nums">
                    {tasksByStatus(col.id).length}
                  </span>
                </div>

                <Droppable droppableId={col.id}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`flex flex-1 flex-col gap-2 p-3 transition-colors min-h-[240px] ${
                        snapshot.isDraggingOver ? col.dropColor : ""
                      }`}
                    >
                      {tasksByStatus(col.id).map((task, index) => (
                        <TaskCard
                          key={task.id}
                          task={task}
                          index={index}
                          assignee={task.assignee_id ? usersById[task.assignee_id] : undefined}
                          onClick={() => setEditingTask(task)}
                        />
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>

                {col.id === "todo" && (
                  <button
                    onClick={() => setCreateForStatus(col.id)}
                    className="flex items-center gap-1.5 rounded-b-2xl border-t border-slate-100 px-4 py-3 text-xs text-slate-400 transition-colors hover:bg-slate-50 hover:text-indigo-600"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add task
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </DragDropContext>

      {createForStatus !== null && (
        <TaskModal
          mode="create"
          projectId={projectId}
          projectDeadline={projectDeadline}
          defaultStatus={createForStatus}
          users={users}
          onDone={() => {
            setCreateForStatus(null);
            queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
          }}
          onClose={() => setCreateForStatus(null)}
        />
      )}

      {editingTask && (
        <TaskModal
          mode="edit"
          task={editingTask}
          projectId={projectId}
          projectDeadline={projectDeadline}
          users={users}
          onDone={() => {
            setEditingTask(null);
            queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
          }}
          onClose={() => setEditingTask(null)}
        />
      )}

      {editingProject && (
        <ProjectEditModal
          projectId={projectId}
          currentTitle={projectTitle}
          currentDeadline={projectDeadline}
          isCompleted={projectCompleted}
          autoComplete={projectAutoComplete}
          tasks={tasks}
          onDone={(updated) => {
            setProjectTitle(updated.title);
            setProjectDeadline(updated.deadline);
            if (updated.completed !== undefined) setProjectCompleted(updated.completed);
            if (updated.auto_complete !== undefined) setProjectAutoComplete(updated.auto_complete);
            setEditingProject(false);
          }}
          onClose={() => setEditingProject(false)}
        />
      )}
    </>
  );
}

// ─── Project edit modal ───────────────────────────────────────────────────────

const projectEditSchema = z.object({
  title: z.string().min(2, "Title must be at least 2 characters."),
  deadline: z.string().min(1, "Deadline is required."),
});
type ProjectEditForm = z.infer<typeof projectEditSchema>;

function ProjectEditModal({
  projectId,
  currentTitle,
  currentDeadline,
  isCompleted,
  autoComplete,
  tasks,
  onDone,
  onClose,
}: {
  projectId: string;
  currentTitle: string;
  currentDeadline: string;
  isCompleted: boolean;
  autoComplete: boolean;
  tasks: Task[];
  onDone: (updated: { title: string; deadline: string; completed?: boolean; auto_complete?: boolean }) => void;
  onClose: () => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [autoCompleteEnabled, setAutoCompleteEnabled] = useState(autoComplete);
  const allTasksDone = tasks.length > 0 && tasks.every((t) => t.completed);
  const toLocalDatetime = (iso: string) => {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<ProjectEditForm>({
    resolver: zodResolver(projectEditSchema),
    defaultValues: {
      title: currentTitle,
      deadline: toLocalDatetime(currentDeadline),
    },
  });

  const { mutate, isPending } = useMutation({
    mutationFn: (v: ProjectEditForm) =>
      api.projects.update(projectId, {
        title: v.title,
        deadline: new Date(v.deadline).toISOString(),
        auto_complete: autoCompleteEnabled,
      }),
    onSuccess: (updated) => {
      toast.success(`Project "${updated.title}" updated.`);
      onDone({ title: updated.title, deadline: updated.deadline, auto_complete: updated.auto_complete });
      queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
      router.refresh();
    },
    onError: (err: Error) => {
      setError("root", { message: err.message });
      toast.error(err.message);
    },
  });

  const { mutate: completeProject, isPending: isCompleting } = useMutation({
    mutationFn: () => api.projects.complete(projectId),
    onSuccess: (updated) => {
      toast.success(`Project "${updated.title}" marked as completed.`);
      onDone({ title: updated.title, deadline: updated.deadline, completed: true });
      queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
      router.refresh();
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });

  const minDeadline = toLocalDatetime(new Date().toISOString());

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Edit project</h2>
            <p className="mt-0.5 text-xs text-slate-400">Update the project details below.</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4 px-6 py-5">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">Project title</Label>
            <Input autoFocus placeholder="e.g. Q2 Roadmap" className="h-10" {...register("title")} />
            {errors.title && <p className="text-xs text-red-500">{errors.title.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">Deadline</Label>
            <Input type="datetime-local" className="h-10" min={minDeadline} {...register("deadline")} />
            {errors.deadline && <p className="text-xs text-red-500">{errors.deadline.message}</p>}
          </div>

          <div className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-700">Auto-complete project</p>
              <p className="mt-0.5 text-xs text-slate-400">Mark project done when all tasks are completed.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={autoCompleteEnabled}
              onClick={() => setAutoCompleteEnabled((v) => !v)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none ${
                autoCompleteEnabled ? "bg-indigo-600" : "bg-slate-200"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform ${
                  autoCompleteEnabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {errors.root && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{errors.root.message}</p>
          )}

          <div className="flex gap-3 pt-1">
            <Button type="button" variant="outline" className="flex-1 h-10" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || isCompleting} className="flex-1 h-10 bg-indigo-600 text-white hover:bg-indigo-700">
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save changes"}
            </Button>
          </div>

          {!isCompleted && (
            <div className="border-t border-slate-100 pt-4 mt-2">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-700">Mark as completed</p>
                  {!allTasksDone && (
                    <p className="mt-0.5 text-xs text-amber-600">
                      All tasks must be completed first ({tasks.filter((t) => !t.completed).length} remaining).
                    </p>
                  )}
                </div>
                <Button
                  type="button"
                  disabled={!allTasksDone || isCompleting || isPending}
                  onClick={() => completeProject()}
                  className="shrink-0 h-9 bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40"
                >
                  {isCompleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Complete project"}
                </Button>
              </div>
            </div>
          )}

          {isCompleted && (
            <div className="border-t border-slate-100 pt-4 mt-2 flex items-center gap-2 text-xs text-emerald-600">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              This project is already marked as completed.
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

// ─── Task card ────────────────────────────────────────────────────────────────

function TaskCard({
  task,
  index,
  assignee,
  onClick,
}: {
  task: Task;
  index: number;
  assignee?: User;
  onClick: () => void;
}) {
  const deadline = new Date(task.deadline);
  const now = new Date();
  const isOverdue = !task.completed && deadline < now;
  const isUrgent = !task.completed && !isOverdue && deadline.getTime() - now.getTime() <= 24 * 60 * 60 * 1000;

  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={onClick}
          className={`rounded-xl border bg-white p-3 shadow-sm select-none cursor-pointer transition-all ${
            snapshot.isDragging
              ? "shadow-xl border-indigo-300 rotate-1 scale-[1.02]"
              : isUrgent
              ? "border-red-300 shadow-[0_0_0_1px_rgba(239,68,68,0.3),0_2px_8px_rgba(239,68,68,0.15)] hover:shadow-[0_0_0_1px_rgba(239,68,68,0.5),0_4px_12px_rgba(239,68,68,0.25)]"
              : "border-slate-200 hover:shadow-md hover:border-indigo-200"
          }`}
        >
          {isUrgent && (
            <div className="mb-2 flex items-center gap-1.5 rounded-md bg-red-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-red-500">
              <AlertCircle className="h-3 w-3 shrink-0" />
              Due within 24 h
            </div>
          )}
          <p className="text-sm font-medium text-slate-800 leading-snug">{task.title}</p>
          {task.description && (
            <p className="mt-1 text-xs text-slate-400 line-clamp-2">{task.description}</p>
          )}
          <div className="mt-3 flex items-center justify-between gap-2">
            <span className={`flex items-center gap-1 text-xs shrink-0 ${isOverdue ? "text-red-500" : "text-slate-400"}`}>
              {isOverdue && <AlertCircle className="h-3 w-3" />}
              <Calendar className="h-3 w-3" />
              {deadline.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </span>

            {assignee ? (
              <span className="flex items-center gap-1.5 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600 truncate max-w-[120px]">
                <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-indigo-200 text-[9px] font-bold text-indigo-700">
                  {assignee.fullname.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                </span>
                <span className="truncate">{assignee.fullname.split(" ")[0]}</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded-full border border-dashed border-slate-200 px-2 py-0.5 text-xs text-slate-300">
                <UserPlus className="h-3 w-3" />
                Unassigned
              </span>
            )}
          </div>
        </div>
      )}
    </Draggable>
  );
}

// ─── Task modal (create + edit) ───────────────────────────────────────────────

function TaskModal({
  mode,
  task,
  projectId,
  projectDeadline,
  defaultStatus,
  users,
  onDone,
  onClose,
}: {
  mode: "create" | "edit";
  task?: Task;
  projectId: string;
  projectDeadline: string;
  defaultStatus?: TaskStatus;
  users: User[];
  onDone: () => void;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();

  // Pre-fill for edit mode
  const toLocalDatetime = (iso: string) => {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const currentAssignee = task?.assignee_id ? users.find((u) => u.id === task.assignee_id) ?? null : null;
  const [selectedUser, setSelectedUser] = useState<User | null>(currentAssignee);
  const [userSearch, setUserSearch] = useState("");
  const [showUserPicker, setShowUserPicker] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<TaskForm>({
    resolver: zodResolver(taskSchema),
    defaultValues: task
      ? {
          title: task.title,
          deadline: toLocalDatetime(task.deadline),
          description: task.description ?? "",
        }
      : undefined,
  });

  const { mutate, isPending } = useMutation({
    mutationFn: async (v: TaskForm) => {
      let saved: Task;
      if (mode === "create") {
        saved = await api.tasks.create({
          title: v.title,
          deadline: new Date(v.deadline).toISOString(),
          description: v.description || undefined,
          project_id: projectId,
        });
      } else {
        saved = await api.tasks.update(task!.id, {
          title: v.title,
          deadline: new Date(v.deadline).toISOString(),
          description: v.description || undefined,
        });
      }
      // Sync assignee
      const prevAssigneeId = task?.assignee_id ?? null;
      const newAssigneeId = selectedUser?.id ?? null;
      if (newAssigneeId && newAssigneeId !== prevAssigneeId) {
        await api.tasks.assign(saved.id, newAssigneeId);
      } else if (!newAssigneeId && prevAssigneeId) {
        await api.tasks.unassign(saved.id);
      }
      return saved;
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["project-tasks", projectId] });
      toast.success(mode === "create" ? `Task "${saved.title}" created.` : `Task "${saved.title}" updated.`);
      onDone();
    },
    onError: (err: Error) => {
      setError("root", { message: err.message });
      toast.error(err.message);
    },
  });

  const filteredUsers = users.filter(
    (u) =>
      u.fullname.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase())
  );

  const columnLabel = COLUMNS.find((c) => c.id === (defaultStatus ?? task?.status))?.label ?? "To Do";
  const maxDeadline = projectDeadline.slice(0, 16);
  const minDeadline = toLocalDatetime(new Date().toISOString());

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {mode === "create" ? "New task" : "Edit task"}
            </h2>
            <p className="mt-0.5 text-xs text-slate-400">
              {mode === "create"
                ? <>Adding to <span className="font-medium text-slate-600">{columnLabel}</span></>
                : "Update the task details below."}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4 px-6 py-5">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">Title</Label>
            <Input autoFocus placeholder="e.g. Design login page" className="h-10" {...register("title")} />
            {errors.title && <p className="text-xs text-red-500">{errors.title.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">Deadline</Label>
            <Input type="datetime-local" className="h-10" min={minDeadline} max={maxDeadline} {...register("deadline")} />
            {errors.deadline && <p className="text-xs text-red-500">{errors.deadline.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">
              Description <span className="text-slate-400 font-normal">(optional)</span>
            </Label>
            <Input placeholder="Add more context..." className="h-10" {...register("description")} />
          </div>

          {/* Assignee picker */}
          <div className="space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">
              Assignee <span className="text-slate-400 font-normal">(optional)</span>
            </Label>
            <button
              type="button"
              onClick={() => setShowUserPicker((v) => !v)}
              className="flex h-10 w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-500 hover:border-slate-300 transition-colors"
            >
              {selectedUser ? (
                <span className="flex items-center gap-2 text-slate-800">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-semibold text-indigo-700">
                    {selectedUser.fullname.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                  </span>
                  {selectedUser.fullname}
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-slate-400">
                  <UserPlus className="h-3.5 w-3.5" />
                  Select a user
                </span>
              )}
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>

            {showUserPicker && (
              <div className="rounded-xl border border-slate-200 bg-white shadow-lg">
                <div className="relative p-2">
                  <Search className="absolute left-4 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                  <Input
                    autoFocus
                    placeholder="Search..."
                    className="h-8 pl-7 text-sm"
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                  />
                </div>
                <div className="max-h-40 overflow-y-auto px-2 pb-2">
                  {selectedUser && (
                    <button
                      type="button"
                      onClick={() => { setSelectedUser(null); setShowUserPicker(false); }}
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-400 hover:bg-slate-50"
                    >
                      <X className="h-3 w-3" /> Remove assignee
                    </button>
                  )}
                  {filteredUsers.length === 0 && (
                    <p className="py-3 text-center text-xs text-slate-400">No users found.</p>
                  )}
                  {filteredUsers.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => { setSelectedUser(u); setShowUserPicker(false); }}
                      className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors ${
                        selectedUser?.id === u.id ? "bg-indigo-50 text-indigo-700" : "hover:bg-slate-50 text-slate-700"
                      }`}
                    >
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-semibold text-indigo-700">
                        {u.fullname.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase()}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-medium">{u.fullname}</span>
                        <span className="block truncate text-xs text-slate-400">{u.email}</span>
                      </span>
                      {selectedUser?.id === u.id && <span className="ml-auto text-xs text-indigo-500">selected</span>}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {errors.root && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{errors.root.message}</p>
          )}

          <div className="flex gap-3 pt-1">
            <Button type="button" variant="outline" className="flex-1 h-10" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending} className="flex-1 h-10 bg-indigo-600 text-white hover:bg-indigo-700">
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "create" ? "Create task" : "Save changes"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
