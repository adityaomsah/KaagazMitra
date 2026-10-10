import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PlaceholderStepProps {
  title: string;
  description: string;
  onBack: () => void;
  onContinue?: () => void;
}

/**
 * Minimal placeholder for the Review and Guidance steps (out of F1b scope).
 * Keeps navigation and the "Step X of 5" indicator consistent.
 */
function PlaceholderStep({
  title,
  description,
  onBack,
  onContinue,
}: PlaceholderStepProps) {
  return (
    <section className="flex flex-col gap-6">
      <header className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          {title}
        </h2>
        <p className="text-base text-muted-foreground">{description}</p>
      </header>
      <p className="rounded-xl border-2 border-dashed border-border bg-card p-6 text-base text-muted-foreground">
        This step is coming in a later part of the build.
      </p>
      <div className="flex items-center justify-between gap-4">
        <Button type="button" variant="outline" size="lg" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back
        </Button>
        {onContinue && (
          <Button type="button" size="lg" onClick={onContinue}>
            Continue
            <ArrowRight className="size-4" aria-hidden="true" />
          </Button>
        )}
      </div>
    </section>
  );
}

export { PlaceholderStep };
