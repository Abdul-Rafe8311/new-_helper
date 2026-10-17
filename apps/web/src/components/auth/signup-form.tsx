"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";

import { FormField } from "./form-field";
import { signupSchema, type SignupValues } from "./schemas";

export function SignupForm() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({ resolver: zodResolver(signupSchema) });

  async function onSubmit(values: SignupValues) {
    try {
      await api.auth.register({
        ...values,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      router.push("/onboarding");
      router.refresh();
    } catch (e) {
      if (e instanceof ApiError && e.code === "email_taken") {
        setError("email", { message: "An account with this email already exists. Sign in instead?" });
        return;
      }
      setError("root", {
        message: e instanceof ApiError ? e.message : "Something went wrong. Please try again.",
      });
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {errors.root ? (
        <p role="alert" className="border-l-2 border-destructive pl-3 font-sans text-sm text-destructive">
          {errors.root.message}
        </p>
      ) : null}
      <FormField
        id="display_name"
        label="Your name"
        autoComplete="name"
        hint="It goes on the front page of your paper."
        error={errors.display_name?.message}
        {...register("display_name")}
      />
      <FormField id="email" label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
      <FormField
        id="password"
        label="Password"
        type="password"
        autoComplete="new-password"
        hint="At least 8 characters."
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" className="su-cta" disabled={isSubmitting}>
        {isSubmitting ? "Setting the presses…" : "Start my paper"}
        <ArrowRight aria-hidden="true" />
      </Button>
    </form>
  );
}
