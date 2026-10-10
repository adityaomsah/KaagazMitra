import { useState } from "react";
import { ArrowLeft, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReviewFieldInput } from "@/components/ReviewFieldInput";
import { check } from "@/lib/api";
import { applyFieldEdit, getReviewFields } from "@/lib/contractGaps";
import { documentTypeLabel } from "@/lib/labels";
import type { PersonaId } from "@/mock";
import type { CheckResponse, Document } from "@/types/api";

/**
 * Step 4 — "Check what we read".
 *
 * One card per extracted document with an editable input per review field
 * (name, date of birth, father's / spouse's name, address, gender — only the
 * ones present). TEMP heuristics (needs-checking badge, transliteration, field
 * name mapping) live in src/lib/contractGaps.ts.
 */

interface StepReviewProps {
  documents: Document[];
  serviceId: string;
  lifeEvents: string[];
  /** Demo persona whose mock check() response to use, if any. */
  personaId: PersonaId | null;
  onBack: () => void;
  onChecked: (result: CheckResponse, editedDocuments: Document[]) => void;
}

function StepReview({
  documents,
  serviceId,
  lifeEvents,
  personaId,
  onBack,
  onChecked,
}: StepReviewProps) {
  // Local editable copy; App remounts this step (via key) when data changes.
  const [edited, setEdited] = useState<Document[]>(documents);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateField = (docId: string, fieldIndex: number, value: string) => {
    setEdited((prev) =>
      prev.map((doc) =>
        doc.id !== docId
          ? doc
          : {
              ...doc,
              fields: doc.fields.map((field, i) =>
                i === fieldIndex ? applyFieldEdit(field, value) : field,
              ),
            },
      ),
    );
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await check(
        { service_id: serviceId, life_events: lifeEvents, documents: edited },
        { personaId },
      );
      onChecked(result, edited);
    } catch {
      setError("We couldn't check your documents just now. Please try again in a moment.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section aria-labelledby="step-review-heading" className="flex flex-col gap-6">
      <header className="space-y-1">
        <h2
          id="step-review-heading"
          className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
        >
          Check what we read
        </h2>
        <p className="text-base text-muted-foreground">
          Look at each detail. If something is wrong, tap it and type it exactly
          as printed on your document.
        </p>
      </header>

      <ul className="flex flex-col gap-4">
        {edited.map((doc) => {
          const fields = getReviewFields(doc);
          return (
            <li
              key={doc.id}
              className="flex flex-col gap-4 rounded-xl border-2 border-border bg-card p-5"
            >
              <div className="flex items-center gap-3">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-primary">
                  <FileText className="size-5" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <h3 className="text-lg font-semibold text-foreground">
                    {documentTypeLabel(doc.document_type)}
                  </h3>
                  <p className="truncate text-sm text-muted-foreground">{doc.filename}</p>
                </div>
              </div>

              {fields.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  We didn't find a name, date or address on this document.
                </p>
              ) : (
                fields.map(({ key, label, index, field }) => (
                  <ReviewFieldInput
                    key={`${key}-${index}`}
                    id={`review-${doc.id}-${index}`}
                    label={label}
                    field={field}
                    onChange={(value) => updateField(doc.id, index, value)}
                  />
                ))
              )}
            </li>
          );
        })}
      </ul>

      {error && (
        <p
          role="status"
          className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground"
        >
          {error}
        </p>
      )}

      <div className="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button type="button" variant="outline" size="lg" onClick={onBack} disabled={submitting}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back
        </Button>
        <Button type="button" size="lg" onClick={handleSubmit} disabled={submitting}>
          {submitting && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {submitting ? "Checking…" : "Looks right - check my documents"}
        </Button>
      </div>
    </section>
  );
}

export { StepReview };
