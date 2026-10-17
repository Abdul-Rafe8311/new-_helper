"use client";

import { useId } from "react";

import { Masthead } from "@/components/paper";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { StepHeading } from "./step-heading";
import type { StepProps } from "./steps-props";

const TIME_ZONES: string[] = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return [];
  }
})();

export function NameStep({ draft, dispatch, today }: StepProps & { today: string }) {
  const nameId = useId();
  const cityId = useId();
  const zoneId = useId();
  const listId = useId();
  return (
    <section>
      <StepHeading
        step={1}
        title="Name your paper"
        lede="It's yours. Make the masthead sound like you."
        why="Your paper name and city go on the masthead and date line of every edition."
      />

      <div className="mb-8" data-testid="masthead-preview" aria-live="polite">
        <Masthead
          paperName={draft.paperName.trim() || "Your paper"}
          date={today}
          timeZone={draft.timezone}
          tagline={draft.city.trim() ? `Printed for ${draft.city.trim()}` : undefined}
          size="md"
        />
      </div>

      <div className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor={nameId}>Paper name</Label>
          <Input
            id={nameId}
            value={draft.paperName}
            maxLength={60}
            autoComplete="off"
            onChange={(e) => dispatch({ type: "set_name", paperName: e.target.value })}
          />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor={cityId}>Your city</Label>
            <Input
              id={cityId}
              value={draft.city}
              maxLength={120}
              autoComplete="address-level2"
              placeholder="Lahore"
              onChange={(e) => dispatch({ type: "set_city", city: e.target.value })}
            />
            <p className="font-sans text-xs text-muted">For the weather and local news.</p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={zoneId}>Time zone</Label>
            <Input
              id={zoneId}
              value={draft.timezone}
              list={listId}
              autoComplete="off"
              spellCheck={false}
              onChange={(e) => dispatch({ type: "set_timezone", timezone: e.target.value })}
            />
            <datalist id={listId}>
              {TIME_ZONES.map((zone) => (
                <option key={zone} value={zone} />
              ))}
            </datalist>
            <p className="font-sans text-xs text-muted">Detected from your device. Your paper lands at 6am here.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
