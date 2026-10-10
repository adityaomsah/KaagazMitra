import { ArrowLeft, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ComparisonList } from "@/components/ComparisonList";
import { EmptyNote, ResultsSection } from "@/components/ResultsSection";
import { READINESS_TEXT } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { CheckResponse, Document } from "@/types/api";

/**
 * Step 5: Results. Layout only for now (details are filled in later).
 * Sections: readiness, what we compared (StatusChip per row), what to do
 * first, what to confirm at the office, sources. All from check().
 */

interface ResultsProps {
  result: CheckResponse;
  documents: Document[];
  /** Show the "Sample data" label (mock mode or demo persona). */
  isSampleData: boolean;
  onBack: () => void;
  onStartOver: () => void;
}

function Results({ result, documents, isSampleData, onBack, onStartOver }: ResultsProps) {
  const { readiness, mismatches, correction_path, sources } = result;
  const verdict = READINESS_TEXT[readiness.status] ?? READINESS_TEXT.UNVERIFIED;
  const officeFindings = readiness.findings.filter(
    (finding) => finding.classification === "VERIFY_AT_OFFICE",
  );
  const correctionSteps = [...correction_path].sort((a, b) => a.order - b.order);
  const hasFirstSteps = readiness.next_steps.length > 0 || correctionSteps.length > 0;
  const hasOfficeItems = officeFindings.length > 0 || readiness.unresolved_questions.length > 0;

  return (
    <section aria-labelledby="results-heading" className="flex flex-col gap-8">
      <header className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h2
            id="results-heading"
            className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
          >
            Your results
          </h2>
          {isSampleData && (
            <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
              Sample data
            </span>
          )}
        </div>
        <p className="text-base text-muted-foreground">
          This is guidance, not a guarantee. The office makes the final decision.
        </p>
      </header>

      <ResultsSection id="results-readiness" title="Your readiness">
        <div className={cn("rounded-xl border-2 p-5", verdict.className)}>
          <p className="text-lg font-semibold text-foreground">{verdict.title}</p>
          <p className="mt-1 text-base text-foreground/80">{verdict.body}</p>
        </div>
      </ResultsSection>

      <ResultsSection id="results-compared" title="What we compared">
        <ComparisonList mismatches={mismatches} documents={documents} />
      </ResultsSection>

      <ResultsSection id="results-first" title="What to do first">
        {!hasFirstSteps ? (
          <EmptyNote>Nothing to do right now.</EmptyNote>
        ) : (
          <div className="flex flex-col gap-4">
            {readiness.next_steps.length > 0 && (
              <ol className="list-decimal space-y-2 pl-6 text-base text-foreground">
                {readiness.next_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            )}
            {correctionSteps.length > 0 && (
              <div className="rounded-xl border-2 border-border bg-card p-4">
                <p className="text-sm font-semibold text-foreground">
                  If a correction is needed, do it in this order:
                </p>
                <ol className="mt-2 list-decimal space-y-2 pl-6 text-base text-foreground">
                  {correctionSteps.map((step) => (
                    <li key={`${step.order}-${step.rule_id}`}>{step.action}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}
      </ResultsSection>

      <ResultsSection id="results-office" title="Please confirm at the office">
        {!hasOfficeItems ? (
          <EmptyNote>Nothing extra to confirm.</EmptyNote>
        ) : (
          <ul className="list-disc space-y-2 pl-6 text-base text-foreground">
            {officeFindings.map((finding, i) => (
              <li key={`finding-${i}`}>{finding.reason}</li>
            ))}
            {readiness.unresolved_questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        )}
      </ResultsSection>

      <ResultsSection id="results-sources" title="Sources">
        {sources.length === 0 ? (
          <EmptyNote>No sources were linked to this result.</EmptyNote>
        ) : (
          <ul className="space-y-2">
            {sources.map((url) => (
              <li key={url}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 break-all text-base text-primary underline-offset-4 hover:underline"
                >
                  {url}
                  <ExternalLink className="size-4 shrink-0" aria-hidden="true" />
                  <span className="sr-only">(opens in a new tab)</span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </ResultsSection>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button type="button" variant="outline" size="lg" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to review
        </Button>
        <Button type="button" variant="secondary" size="lg" onClick={onStartOver}>
          Start over
        </Button>
      </div>
    </section>
  );
}

export { Results };
