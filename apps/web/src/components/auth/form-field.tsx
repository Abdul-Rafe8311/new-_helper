"use client";

import { AlertCircle, Eye, EyeOff } from "lucide-react";
import { useState, type ComponentProps } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type FormFieldProps = ComponentProps<typeof Input> & {
  id: string;
  label: string;
  error?: string;
  hint?: string;
};

/** Label, control, then hint or error. Password fields get a show/hide toggle. */
export function FormField({ id, label, error, hint, type, className, ...input }: FormFieldProps) {
  const [shown, setShown] = useState(false);
  const isPassword = type === "password";
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={isPassword && shown ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={isPassword ? `pr-12 ${className ?? ""}` : className}
          {...input}
        />
        {isPassword ? (
          <button
            type="button"
            aria-label={shown ? "Hide characters" : "Show characters"}
            aria-pressed={shown}
            onClick={() => setShown((v) => !v)}
            className="absolute top-1/2 right-1.5 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-full text-muted outline-none hover:bg-ink/8 hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            {shown ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
          </button>
        ) : null}
      </div>
      {error ? (
        <p id={`${id}-error`} className="flex items-start gap-1.5 font-sans text-sm text-destructive">
          <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="font-sans text-xs text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
