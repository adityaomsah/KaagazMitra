import { Eye } from "lucide-react";
import { getTransliteration, needsChecking } from "@/lib/contractGaps";
import { cn } from "@/lib/utils";
import type { ExtractedField } from "@/types/api";

interface ReviewFieldInputProps {
  /** Unique DOM id for the input. */
  id: string;
  label: string;
  field: ExtractedField;
  onChange: (value: string) => void;
}

/**
 * One editable extracted field on the Review step: label, saffron
 * "Please check this" badge when uncertain, an input showing raw_value
 * (original script preserved) and a small grey transliteration line.
 */
function ReviewFieldInput({ id, label, field, onChange }: ReviewFieldInputProps) {
  const flag = needsChecking(field);
  const transliteration = getTransliteration(field);
  const hintId = `${id}-hint`;
  const badgeId = `${id}-badge`;
  const describedBy = [flag ? badgeId : null, transliteration ? hintId : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        {flag && (
          <span
            id={badgeId}
            className="inline-flex items-center gap-1 rounded-full bg-accent px-2.5 py-0.5 text-xs font-semibold text-accent-foreground"
          >
            <Eye className="size-3.5" aria-hidden="true" />
            Please check this
          </span>
        )}
      </div>
      <input
        id={id}
        type="text"
        value={field.raw_value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={flag ? "We couldn't read this clearly. Please type it." : undefined}
        aria-describedby={describedBy || undefined}
        className={cn(
          "h-12 w-full rounded-lg border-2 bg-background px-3 text-base text-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          flag ? "border-accent-foreground/40 bg-accent/20" : "border-input",
        )}
      />
      {transliteration && (
        <p id={hintId} className="text-xs text-muted-foreground">
          In English letters: {transliteration}
        </p>
      )}
    </div>
  );
}

export { ReviewFieldInput };
