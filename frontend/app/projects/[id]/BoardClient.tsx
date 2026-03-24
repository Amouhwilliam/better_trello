"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Plus, X, Loader2, UserPlus, Search, Calendar, AlertCircle, ChevronDown,
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
  projectDeadline,
}: {
  projectId: string;
  userId: string;
  projectDeadline: string;
}) {
  const queryClient = useQueryClient();
  const [createForStatus, setCreateForStatus] = useState<TaskStatus | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["project-tasks", projectId],
    queryFn: () => api.projects.tasks(projectId),
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
    </>
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
  const isOverdue = !task.completed && deadline < new Date();

  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={onClick}
          className={`rounded-xl border bg-white p-3 shadow-sm select-none cursor-pointer transition-shadow ${
            snapshot.isDragging
              ? "shadow-xl border-indigo-300 rotate-1 scale-[1.02]"
              : "border-slate-200 hover:shadow-md hover:border-indigo-200"
          }`}
        >
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
