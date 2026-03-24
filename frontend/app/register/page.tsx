"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { Loader2, Kanban, ArrowLeft, Eye, EyeOff } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

const schema = z.object({
  email: z.email("Please enter a valid email address."),
  fullname: z.string().min(2, "Full name must be at least 2 characters."),
  password: z.string().min(6, "Password must be at least 6 characters."),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const { mutate, isPending } = useMutation({
    mutationFn: async (values: FormValues) => {
      const user = await api.users.create({
        fullname: values.fullname,
        email: values.email,
        password: values.password,
      });
      const loginRes = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: values.email, password: values.password }),
      });
      if (!loginRes.ok) throw new Error("Account created but sign-in failed. Please sign in.");
      return user;
    },
    onSuccess: () => router.push("/dashboard"),
    onError: (err: Error) => setError("root", { message: err.message }),
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
            <p className="mt-1 text-sm text-slate-500">Just a few details and you&apos;re good to go.</p>
          </div>

          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-700">Email address</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
                className="h-11"
                {...register("email")}
              />
              {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="fullname" className="text-sm font-medium text-slate-700">Full name</Label>
              <Input id="fullname" placeholder="Alice Dupont" className="h-11" {...register("fullname")} />
              {errors.fullname && <p className="text-xs text-red-500">{errors.fullname.message}</p>}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-slate-700">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  className="h-11 pr-10"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
            </div>

            {errors.root && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{errors.root.message}</p>
            )}

            <Button type="submit" disabled={isPending} className="h-11 w-full bg-indigo-600 text-white hover:bg-indigo-700">
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create account"}
            </Button>
          </form>
        </div>

        <div className="mt-4 flex justify-center">
          <Link href="/" className="flex items-center gap-1.5 text-xs text-slate-400 transition-colors hover:text-slate-600">
            <ArrowLeft className="h-3 w-3" />
            Back
          </Link>
        </div>
      </div>
    </div>
  );
}
