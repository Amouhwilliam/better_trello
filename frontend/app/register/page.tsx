"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { Loader2, Kanban, ArrowLeft } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";

const schema = z.object({
  fullname: z.string().min(2, "Full name must be at least 2 characters."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string }>;
}) {
  const { email = "" } = use(searchParams);
  const router = useRouter();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) =>
      api.users.create({ fullname: values.fullname, email, password: values.password }),
    onSuccess: (user) => router.push(`/dashboard?userId=${user.id}`),
    onError: (err: Error) =>
      setError("root", { message: err.message }),
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-200">
            <Kanban className="h-7 w-7 text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Better Trello</h1>
            <p className="mt-1 text-sm text-slate-500">Task management, beautifully simple.</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/60">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-900">Create your account</h2>
            <p className="mt-1 text-sm text-slate-500">
              Just a few details and you&apos;re good to go.
            </p>
          </div>

          {/* Email (read-only) */}
          <div className="mb-5 space-y-1.5">
            <Label className="text-sm font-medium text-slate-700">Email address</Label>
            <div className="flex h-11 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500">
              {email}
            </div>
          </div>

          <Separator className="mb-5" />

          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="fullname" className="text-sm font-medium text-slate-700">
                Full name
              </Label>
              <Input
                id="fullname"
                placeholder="Alice Dupont"
                autoFocus
                className="h-11"
                {...register("fullname")}
              />
              {errors.fullname && (
                <p className="text-xs text-red-500">{errors.fullname.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-slate-700">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                className="h-11"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-xs text-red-500">{errors.password.message}</p>
              )}
            </div>

            {errors.root && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">
                {errors.root.message}
              </p>
            )}

            <Button
              type="submit"
              disabled={isPending}
              className="h-11 w-full bg-indigo-600 text-white hover:bg-indigo-700"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Create account"
              )}
            </Button>
          </form>
        </div>

        <div className="mt-4 flex justify-center">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600"
          >
            <ArrowLeft className="h-3 w-3" />
            Back
          </Link>
        </div>
      </div>
    </div>
  );
}
