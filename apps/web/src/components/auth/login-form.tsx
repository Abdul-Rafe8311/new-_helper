"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { safeNext } from "@/lib/safe-next";

import { FormField } from "./form-field";
import { loginSchema, type LoginValues } from "./schemas";

export function LoginForm() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginValues) {
    try {
      await api.auth.login(values);
      router.push(safeNext(new URLSearchParams(window.location.search).get("next")));
      router.refresh();
    } catch (e) {
      setError("root", {
        message: e instanceof ApiError ? e.message : "Something went wrong. Please try again.",
      });
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {errors.root ? (
        <p role="alert" className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 font-sans text-sm text-destructive">
          {errors.root.message}
        </p>
      ) : null}
      <FormField id="email" label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
      <FormField
        id="password"
        label="Password"
        type="password"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" variant="accent" size="lg" className="w-full justify-between" disabled={isSubmitting} aria-busy={isSubmitting}>
        {isSubmitting ? "Signing in…" : "Sign in"}
        {isSubmitting ? <Loader2 aria-hidden="true" className="animate-spin" /> : <ArrowRight aria-hidden="true" />}
      </Button>
    </form>
  );
}
