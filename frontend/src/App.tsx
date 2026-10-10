import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { DemoSwitch, PersonaButtons } from "@/components/DemoBar";
import { ProgressBar } from "@/components/ProgressBar";
import { StepService } from "@/pages/StepService";
import { StepSituation } from "@/pages/StepSituation";
import { StepDocuments } from "@/pages/StepDocuments";
import { StepReview } from "@/pages/StepReview";
import { Results } from "@/pages/Results";
import { extract, isMockMode } from "@/lib/api";
import { getPersona, type PersonaId } from "@/mock";
import type { CheckResponse, Document, DocumentType } from "@/types/api";
import {
  TOTAL_STEPS,
  initialAnswers,
  type LifeEvent,
  type UploadedDocument,
  type WizardAnswers,
} from "@/types/wizard";

const MAX_DOCUMENTS = 5;

/** Generate a stable-enough unique id for an uploaded document. */
let docCounter = 0;
function makeDocId(): string {
  docCounter += 1;
  return `doc_${Date.now()}_${docCounter}`;
}

/**
 * App hosts the five-step wizard and owns the shared state: the answers object
 * (service_id, life_events, uploads, consent), the extracted documents shown
 * on Review, the check() result shown on Results, and the demo persona.
 */
function App() {
  const [step, setStep] = useState(1);
  const [answers, setAnswers] = useState<WizardAnswers>(initialAnswers);
  /** Documents returned by extract() (or a demo persona), edited on Review. */
  const [extracted, setExtracted] = useState<Document[]>([]);
  const [checkResult, setCheckResult] = useState<CheckResponse | null>(null);
  const [demoOn, setDemoOn] = useState(false);
  /** Persona whose mock data is in use; null for the normal upload flow. */
  const [personaId, setPersonaId] = useState<PersonaId | null>(null);
  /** Bumped on new data so StepReview remounts with a fresh editable copy. */
  const [reviewKey, setReviewKey] = useState(0);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  // Track created object URLs so we can revoke them on remove / unmount.
  const previewUrlsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    const urls = previewUrlsRef.current;
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
      urls.clear();
    };
  }, []);

  const selectService = useCallback((serviceId: string) => {
    setAnswers((prev) => ({ ...prev, service_id: serviceId }));
  }, []);

  const answerLifeEvent = useCallback((event: LifeEvent, value: boolean) => {
    setAnswers((prev) => {
      const has = prev.life_events.includes(event);
      if (value && !has) {
        return { ...prev, life_events: [...prev.life_events, event] };
      }
      if (!value && has) {
        return {
          ...prev,
          life_events: prev.life_events.filter((e) => e !== event),
        };
      }
      return prev;
    });
  }, []);

  const addFiles = useCallback((files: File[]) => {
    setAnswers((prev) => {
      const room = MAX_DOCUMENTS - prev.documents.length;
      if (room <= 0) return prev;
      const added: UploadedDocument[] = files.slice(0, room).map((file) => {
        const previewUrl = URL.createObjectURL(file);
        previewUrlsRef.current.add(previewUrl);
        return { id: makeDocId(), file, previewUrl, documentType: "" };
      });
      return { ...prev, documents: [...prev.documents, ...added] };
    });
  }, []);

  const removeDocument = useCallback((id: string) => {
    setAnswers((prev) => {
      const target = prev.documents.find((doc) => doc.id === id);
      if (target) {
        URL.revokeObjectURL(target.previewUrl);
        previewUrlsRef.current.delete(target.previewUrl);
      }
      return {
        ...prev,
        documents: prev.documents.filter((doc) => doc.id !== id),
      };
    });
  }, []);

  const setDocumentType = useCallback((id: string, type: DocumentType) => {
    setAnswers((prev) => ({
      ...prev,
      documents: prev.documents.map((doc) =>
        doc.id === id ? { ...doc, documentType: type } : doc,
      ),
    }));
  }, []);

  const setConsent = useCallback((consent: boolean) => {
    setAnswers((prev) => ({ ...prev, consent }));
  }, []);

  const goNext = () => setStep((s) => Math.min(TOTAL_STEPS, s + 1));
  const goBack = () => setStep((s) => Math.max(1, s - 1));

  /** Step 3 -> 4: read the uploaded documents, then show them for review. */
  const extractAndReview = async () => {
    setExtracting(true);
    setExtractError(null);
    try {
      const docs = await extract(answers.documents, answers.consent);
      setPersonaId(null);
      setExtracted(docs);
      setCheckResult(null);
      setReviewKey((k) => k + 1);
      setStep(4);
    } catch {
      setExtractError(
        "We couldn't read your documents just now. Please check your connection and try again.",
      );
    } finally {
      setExtracting(false);
    }
  };

  /** Demo: jump straight to Review with a persona's mock data. */
  const loadPersona = (id: PersonaId) => {
    const persona = getPersona(id);
    setAnswers((prev) => ({
      ...prev,
      service_id: persona.service_id,
      life_events: [...persona.life_events],
      consent: true,
    }));
    setPersonaId(id);
    setExtracted(JSON.parse(JSON.stringify(persona.documents)) as Document[]);
    setCheckResult(null);
    setExtractError(null);
    setReviewKey((k) => k + 1);
    setStep(4);
  };

  const handleChecked = (result: CheckResponse, edited: Document[]) => {
    setExtracted(edited); // keep the user's edits if they go back to Review
    setCheckResult(result);
    setStep(5);
  };

  const startOver = () => {
    previewUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    previewUrlsRef.current.clear();
    setAnswers(initialAnswers);
    setExtracted([]);
    setCheckResult(null);
    setPersonaId(null);
    setExtractError(null);
    setStep(1);
  };

  const isSampleData = isMockMode() || personaId !== null;

  return (
    <main className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex min-h-svh max-w-2xl flex-col gap-8 px-4 py-8 sm:px-6">
        <header className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <span className="text-2xl font-bold tracking-tight text-primary">
              KaagazMitra
            </span>
            <DemoSwitch on={demoOn} onToggle={setDemoOn} />
          </div>
          {demoOn && <PersonaButtons activePersona={personaId} onLoad={loadPersona} />}
          <ProgressBar current={step} total={TOTAL_STEPS} />
        </header>

        <div className="flex-1">
          {step === 1 && (
            <StepService
              selected={answers.service_id}
              onSelect={selectService}
              onBack={goBack}
              onContinue={goNext}
            />
          )}

          {step === 2 && (
            <StepSituation
              lifeEvents={answers.life_events}
              onAnswer={answerLifeEvent}
              onBack={goBack}
              onContinue={goNext}
            />
          )}

          {step === 3 && (
            <div className="flex flex-col gap-4">
              <StepDocuments
                documents={answers.documents}
                consent={answers.consent}
                onAddFiles={addFiles}
                onRemove={removeDocument}
                onTypeChange={setDocumentType}
                onConsentChange={setConsent}
                onBack={goBack}
                onContinue={() => {
                  if (!extracting) void extractAndReview();
                }}
              />
              {extracting && (
                <p
                  role="status"
                  className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground"
                >
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Reading your documents…
                </p>
              )}
              {extractError && !extracting && (
                <p
                  role="status"
                  className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground"
                >
                  {extractError}
                </p>
              )}
            </div>
          )}

          {step === 4 && (
            <StepReview
              key={reviewKey}
              documents={extracted}
              serviceId={answers.service_id ?? ""}
              lifeEvents={answers.life_events}
              personaId={personaId}
              onBack={goBack}
              onChecked={handleChecked}
            />
          )}

          {step === 5 && checkResult && (
            <Results
              result={checkResult}
              documents={extracted}
              isSampleData={isSampleData}
              onBack={() => setStep(4)}
              onStartOver={startOver}
            />
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
