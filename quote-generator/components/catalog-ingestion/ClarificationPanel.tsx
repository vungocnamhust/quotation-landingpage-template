"use client";

import { useState } from "react";
import { getTypographyClassName } from "../../config/typography.ts";
import { cn } from "../../utils/cn.ts";
import type { IngestionClarification } from "./types.ts";

interface Props {
  clarifications: IngestionClarification[];
  roundsUsed: number;
  maxRounds: number;
  isSubmitting: boolean;
  onSubmit: (answers: Record<string, string>) => void;
}

export function ClarificationPanel({ clarifications, roundsUsed, maxRounds, isSubmitting, onSubmit }: Props) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  if (clarifications.length === 0) return null;

  const blocking = clarifications.filter((c) => c.blocking);
  const allAnswered = blocking.every((c) => (drafts[c.id] ?? "").trim().length > 0);

  return (
    <section className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-amber-500/40 bg-amber-500/5 p-5 shadow-xs">
      <div className="flex items-center justify-between gap-2">
        <h2 className={cn(getTypographyClassName("cardTitle"), "text-[var(--color-on-surface)]")}>
          The Resolver Co-Pilot has questions
        </h2>
        <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>
          Round {roundsUsed} of {maxRounds}
        </span>
      </div>

      <div className="flex flex-col gap-4">
        {clarifications.map((clarification) => (
          <div key={clarification.id} className="flex flex-col gap-2 rounded-[var(--radius-input)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-4">
            <p className={cn(getTypographyClassName("bodyMd"), "text-[var(--color-on-surface)]")}>
              {clarification.question}
            </p>
            {clarification.source_quote ? (
              <blockquote
                className={cn(
                  getTypographyClassName("quote"),
                  "border-l-2 border-[var(--color-border-strong)] pl-3 text-[var(--color-muted)]",
                )}
              >
                “{clarification.source_quote}”
              </blockquote>
            ) : null}

            {clarification.options && clarification.options.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {clarification.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setDrafts((prev) => ({ ...prev, [clarification.id]: option }))}
                    className={cn(
                      getTypographyClassName("buttonSecondary"),
                      "rounded-full border px-3 py-1.5 transition-colors",
                      drafts[clarification.id] === option
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-wash)] text-[var(--color-accent)]"
                        : "border-[var(--color-border-strong)] text-[var(--color-on-surface)] hover:bg-[var(--color-surface-hover)]",
                    )}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type="text"
                value={drafts[clarification.id] ?? ""}
                onChange={(event) => setDrafts((prev) => ({ ...prev, [clarification.id]: event.target.value }))}
                placeholder="Type your answer…"
                className={cn(
                  getTypographyClassName("bodySm"),
                  "rounded-[var(--radius-input)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 py-2 text-[var(--color-on-surface)] outline-none focus:border-[var(--color-accent)]",
                )}
              />
            )}
            {!clarification.blocking ? (
              <span className={cn(getTypographyClassName("caption"), "text-[var(--color-muted)]")}>Optional</span>
            ) : null}
          </div>
        ))}
      </div>

      <button
        type="button"
        disabled={!allAnswered || isSubmitting}
        onClick={() => onSubmit(drafts)}
        className={cn(
          getTypographyClassName("buttonPrimary"),
          "w-fit rounded-[var(--radius-button)] bg-[var(--color-accent)] px-4 py-2.5 text-white shadow-xs transition-all hover:bg-[color-mix(in_srgb,var(--color-accent)_85%,black)] disabled:cursor-not-allowed disabled:opacity-50",
        )}
      >
        {isSubmitting ? "Submitting…" : "Submit answers"}
      </button>
    </section>
  );
}
