import { useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { ArrowLeft, ImagePlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { DocumentType } from "@/types/api";
import type { UploadedDocument } from "@/types/wizard";

/**
 * Step 3 — "Add photos of your documents".
 *
 * Up to 5 upload cards (tap or drag-and-drop). Each added document shows an
 * image preview, a document-type dropdown (only values allowed by
 * src/types/api.ts) and a remove button. A consent checkbox must be ticked
 * before continuing. Continue is enabled only when there is at least one
 * document, every document has a type, and consent is given. Helper messages
 * are gentle and never red.
 */

const MAX_DOCUMENTS = 5;

// Only DocumentType values from src/types/api.ts. "Land record" maps to
// "other" because there is no dedicated enum value for it.
interface TypeOption {
  value: DocumentType;
  label: string;
}

const TYPE_OPTIONS: TypeOption[] = [
  { value: "aadhaar", label: "Aadhaar" },
  { value: "pan", label: "PAN" },
  { value: "bank_passbook", label: "Bank passbook" },
  { value: "class10_marksheet", label: "Class 10 marksheet" },
  { value: "marriage_certificate", label: "Marriage certificate" },
  { value: "other", label: "Land record" },
  { value: "other", label: "Other" },
];

interface StepDocumentsProps {
  documents: UploadedDocument[];
  consent: boolean;
  onAddFiles: (files: File[]) => void;
  onRemove: (id: string) => void;
  onTypeChange: (id: string, type: DocumentType) => void;
  onConsentChange: (consent: boolean) => void;
  onBack: () => void;
  onContinue: () => void;
}

function StepDocuments({
  documents,
  consent,
  onAddFiles,
  onRemove,
  onTypeChange,
  onConsentChange,
  onBack,
  onContinue,
}: StepDocumentsProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputId = "step-documents-file-input";

  const slotsLeft = MAX_DOCUMENTS - documents.length;
  const canAdd = slotsLeft > 0;

  const hasDocument = documents.length > 0;
  const allTyped = documents.every((doc) => doc.documentType !== "");
  const canContinue = hasDocument && allTyped && consent;

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length > 0) {
      onAddFiles(files);
    }
    // Reset so selecting the same file again still fires a change event.
    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (!canAdd) return;
    const files = Array.from(event.dataTransfer.files ?? []);
    if (files.length > 0) {
      onAddFiles(files);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (canAdd) setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  // A gentle, single helper line describing what is still needed. Never red.
  let helper: string | null = null;
  if (!hasDocument) {
    helper = "Add at least one photo of your document to continue.";
  } else if (!allTyped) {
    helper = "Please choose a document type for each photo.";
  } else if (!consent) {
    helper = "Please tick the consent box to continue.";
  }


  return (
    <section
      aria-labelledby="step-documents-heading"
      className="flex flex-col gap-6"
    >
      <header className="space-y-1">
        <h2
          id="step-documents-heading"
          className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
        >
          Add photos of your documents
        </h2>
        <p className="text-base text-muted-foreground">
          Take a clear photo of each document. You can add up to {MAX_DOCUMENTS}.
        </p>
      </header>

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {documents.map((doc) => (
          <li
            key={doc.id}
            className="flex flex-col gap-3 rounded-xl border-2 border-border bg-card p-4"
          >
            <div className="relative">
              <img
                src={doc.previewUrl}
                alt={`Preview of ${doc.file.name}`}
                className="h-40 w-full rounded-lg border border-border object-cover"
              />
              <button
                type="button"
                onClick={() => onRemove(doc.id)}
                aria-label={`Remove ${doc.file.name}`}
                className={cn(
                  "absolute right-2 top-2 flex size-9 items-center justify-center rounded-full bg-card/90 text-destructive shadow-sm transition-colors",
                  "hover:bg-destructive hover:text-destructive-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                )}
              >
                <Trash2 className="size-5" aria-hidden="true" />
              </button>
            </div>

            <label
              htmlFor={`doc-type-${doc.id}`}
              className="text-sm font-medium text-foreground"
            >
              Document type
            </label>
            <select
              id={`doc-type-${doc.id}`}
              value={doc.documentType}
              onChange={(event) =>
                onTypeChange(doc.id, event.target.value as DocumentType)
              }
              className={cn(
                "h-12 w-full rounded-lg border-2 border-input bg-background px-3 text-base text-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                doc.documentType === "" && "text-muted-foreground",
              )}
            >
              <option value="" disabled>
                Choose a document type
              </option>
              {TYPE_OPTIONS.map((option, index) => (
                <option key={`${option.value}-${index}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <p className="truncate text-sm text-muted-foreground">
              {doc.file.name}
            </p>
          </li>
        ))}

        {canAdd && (
          <li>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={cn(
                "flex h-full min-h-56 flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition-colors",
                isDragging ? "border-primary bg-accent/30" : "border-input bg-card",
              )}
            >
              <ImagePlus className="size-8 text-primary" aria-hidden="true" />
              <label
                htmlFor={inputId}
                className="cursor-pointer text-base font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                Tap to add a photo
              </label>
              <p className="text-sm text-muted-foreground">
                or drag and drop it here
              </p>
              <input
                ref={fileInputRef}
                id={inputId}
                type="file"
                accept="image/*"
                multiple
                onChange={handleInputChange}
                className="sr-only"
              />
            </div>
          </li>
        )}
      </ul>

      <label
        htmlFor="documents-consent"
        className="flex items-start gap-3 rounded-xl border-2 border-border bg-card p-4"
      >
        <input
          id="documents-consent"
          type="checkbox"
          checked={consent}
          onChange={(event) => onConsentChange(event.target.checked)}
          className={cn(
            "mt-0.5 size-6 shrink-0 accent-[var(--primary)]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          )}
        />
        <span className="text-base text-foreground">
          I agree that my document images are sent to a cloud AI service to read
          them. KaagazMitra does not store them.
        </span>
      </label>

      {helper && (
        <p role="status" className="text-sm text-muted-foreground">
          {helper}
        </p>
      )}

      <div className="mt-2 flex items-center justify-between gap-4">
        <Button type="button" variant="outline" size="lg" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back
        </Button>
        <Button
          type="button"
          size="lg"
          onClick={onContinue}
          disabled={!canContinue}
        >
          Continue
        </Button>
      </div>
    </section>
  );
}

export { StepDocuments };
