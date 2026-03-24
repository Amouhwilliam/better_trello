"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { Loader2, Kanban, ArrowRight } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Please enter a valid email address."),
});
type FormValues = z.infer<typeof schema>;

async function lookupEmail(email: string) {
  const res = await fetch(`/api/users/lookup?email=${encodeURIComponent(email)}`);
  if (res.status === 404) return { exists: false, user: null };
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? "Something went wrong. Please try again.");
  }
  return res.json() as Promise<{ exists: boolean; user: { id: string } }>;
}

export default function HomePage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const { mutate, isPending } = useMutation({
    mutationFn: (email: string) => lookupEmail(email),
    onSuccess: (data) => {
      const email = getValues("email");
      if (data.exists && data.user) {
        router.push(`/dashboard?userId=${data.user.id}`);
      } else {
        router.push(`/register?email=${encodeURIComponent(email)}`);
      }
    },
    onError: (err: Error) => setServerError(err.message),
  });

  const onSubmit = (values: FormValues) => {
    setServerError(null);
    mutate(values.email);
  };

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
            <h2 className="text-lg font-semibold text-slate-900">Welcome back</h2>
            <p className="mt-1 text-sm text-slate-500">
              Enter your email to continue or create an account.
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-700">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
                className="h-11"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-xs text-red-500">{errors.email.message}</p>
              )}
              {serverError && (
                <p className="text-xs text-red-500">{serverError}</p>
              )}
            </div>

            <Button
              type="submit"
              disabled={isPending}
              className="h-11 w-full bg-indigo-600 text-white hover:bg-indigo-700"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  Continue
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-slate-400">
          No account?{" "}
          <Link href="/register" className="text-indigo-500 hover:text-indigo-700 underline underline-offset-2">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
