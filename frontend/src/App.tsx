import { useCallback, useEffect, useRef, useState } from "react";
import { ProgressBar } from "@/components/ProgressBar";
import { StepService } from "@/pages/StepService";
import { StepSituation } from "@/pages/StepSituation";
import { StepDocuments } from "@/pages/StepDocuments";
import { PlaceholderStep } from "@/pages/PlaceholderStep";
import type { DocumentType } from "@/types/api";
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
 * App hosts the five-step wizard and owns the single shared answers object:
 * service_id, life_events, uploaded documents (with types) and consent.
 * Steps 4 (Review) and 5 (Guidance) are minimal placeholders (out of F1b scope).
 */
function App() {
  const [step, setStep] = useState(1);
  const [answers, setAnswers] = useState<WizardAnswers>(initialAnswers);

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

  return (
    <main className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex min-h-svh max-w-2xl flex-col gap-8 px-4 py-8 sm:px-6">
        <header className="space-y-4">
          <span className="text-2xl font-bold tracking-tight text-primary">
            KaagazMitra
          </span>
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
            <StepDocuments
              documents={answers.documents}
              consent={answers.consent}
              onAddFiles={addFiles}
              onRemove={removeDocument}
              onTypeChange={setDocumentType}
              onConsentChange={setConsent}
              onBack={goBack}
              onContinue={goNext}
            />
          )}

          {step === 4 && (
            <PlaceholderStep
              title="Review"
              description="We'll bring together your service, situation and documents so you can confirm everything before we check them."
              onBack={goBack}
              onContinue={goNext}
            />
          )}

          {step === 5 && (
            <PlaceholderStep
              title="Guidance"
              description="Your personalised readiness guidance will appear here."
              onBack={goBack}
            />
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
