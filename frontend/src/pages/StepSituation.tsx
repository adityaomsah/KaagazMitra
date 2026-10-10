import { useState } from "react";
import { ArrowLeft, Check, MoveRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LifeEvent } from "@/types/wizard";

/**
 * Step 2 — "Your situation".
 *
 * One question per screen with large Yes / No buttons, then a short summary of
 * the life events we'll check for. The three answers map to life_events ids
 * used by the readiness check. The sub-flow position is local UI state; the
 * answers themselves live in the shared wizard state in App.tsx.
 */

interface Question {
  event: LifeEvent;
  prompt: string;
  /** Friendly phrase used in the summary list. */
  summary: string;
}

const QUESTIONS: Question[] = [
  {
    event: "name_change",
    prompt: "Has your name or surname changed? (for example, after marriage)",
    summary: "a name or surname change",
  },
  {
    event: "address_change",
    prompt: "Have you moved to a new address?",
    summary: "a change of address",
  },
  {
    event: "dob_difference",
    prompt: "Is your date of birth different on any document?",
    summary: "a difference in date of birth",
  },
];

interface StepSituationProps {
  lifeEvents: LifeEvent[];
  /** Add (true) or remove (false) a life event from the shared state. */
  onAnswer: (event: LifeEvent, value: boolean) => void;
  onBack: () => void;
  onContinue: () => void;
}


function StepSituation({
  lifeEvents,
  onAnswer,
  onBack,
  onContinue,
}: StepSituationProps) {
  // index 0..2 = question screens, 3 = summary screen.
  const [index, setIndex] = useState(0);
  const isSummary = index >= QUESTIONS.length;
  const question = QUESTIONS[Math.min(index, QUESTIONS.length - 1)];

  const handleAnswer = (value: boolean) => {
    onAnswer(question.event, value);
    setIndex((i) => i + 1);
  };

  const handleBack = () => {
    if (index === 0) {
      onBack();
    } else {
      setIndex((i) => i - 1);
    }
  };

  // Phrases for the events the user answered "Yes" to, in catalog order.
  const selectedSummaries = QUESTIONS.filter((q) =>
    lifeEvents.includes(q.event),
  ).map((q) => q.summary);

  return (
    <section
      aria-labelledby="step-situation-heading"
      className="flex flex-col gap-6"
    >
      <header className="space-y-1">
        <h2
          id="step-situation-heading"
          className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
        >
          Your situation
        </h2>
        <p className="text-base text-muted-foreground">
          A few quick yes / no questions help us know what to look for.
        </p>
      </header>

      {isSummary ? (
        <div className="flex flex-col gap-6">
          <div className="rounded-xl border-2 border-border bg-card p-6">
            <h3 className="text-lg font-semibold text-foreground">
              We'll check for:
            </h3>
            {selectedSummaries.length > 0 ? (
              <ul className="mt-3 space-y-2">
                {selectedSummaries.map((summary) => (
                  <li
                    key={summary}
                    className="flex items-start gap-2 text-base text-foreground"
                  >
                    <Check
                      className="mt-0.5 size-5 shrink-0 text-primary"
                      aria-hidden="true"
                    />
                    <span className="capitalize">{summary}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-base text-muted-foreground">
                Nothing extra right now — we'll still compare the details on
                your documents.
              </p>
            )}
          </div>

          <div className="flex items-center justify-between gap-4">
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => setIndex(QUESTIONS.length - 1)}
            >
              <ArrowLeft className="size-4" aria-hidden="true" />
              Back
            </Button>
            <Button type="button" size="lg" onClick={onContinue}>
              Continue
              <MoveRight className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <p
            aria-live="polite"
            className="rounded-xl border-2 border-border bg-card p-6 text-xl font-semibold text-foreground"
          >
            {question.prompt}
          </p>

          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => handleAnswer(true)}
              className={cn(
                "flex h-20 items-center justify-center rounded-xl border-2 border-primary bg-primary text-xl font-semibold text-primary-foreground transition-colors",
                "hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              )}
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => handleAnswer(false)}
              className={cn(
                "flex h-20 items-center justify-center rounded-xl border-2 border-border bg-card text-xl font-semibold text-foreground transition-colors",
                "hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              )}
            >
              No
            </button>
          </div>

          <p className="text-sm text-muted-foreground" role="status">
            Question {index + 1} of {QUESTIONS.length}
          </p>

          <div className="flex items-center justify-start">
            <Button type="button" variant="outline" size="lg" onClick={handleBack}>
              <ArrowLeft className="size-4" aria-hidden="true" />
              Back
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

export { StepSituation };
