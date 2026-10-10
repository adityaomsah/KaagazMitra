import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PERSONAS, type PersonaId } from "@/mock";

interface DemoSwitchProps {
  on: boolean;
  onToggle: (on: boolean) => void;
}

/** Small "Demo" toggle for the top bar. */
function DemoSwitch({ on, onToggle }: DemoSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={() => onToggle(!on)}
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-1 py-1 text-sm font-medium text-muted-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      )}
    >
      Demo
      <span
        aria-hidden="true"
        className={cn(
          "relative inline-flex h-6 w-10 items-center rounded-full transition-colors",
          on ? "bg-primary" : "bg-input",
        )}
      >
        <span
          className={cn(
            "inline-block size-5 rounded-full bg-card shadow-sm transition-transform",
            on ? "translate-x-[18px]" : "translate-x-0.5",
          )}
        />
      </span>
    </button>
  );
}

interface PersonaButtonsProps {
  activePersona: PersonaId | null;
  onLoad: (id: PersonaId) => void;
}

/** "Load Anita" / "Load Rahim" / "Load Ramesh": jump to Review with mock data. */
function PersonaButtons({ activePersona, onLoad }: PersonaButtonsProps) {
  return (
    <div
      role="group"
      aria-label="Demo personas"
      className="flex flex-wrap items-center gap-2 rounded-xl border border-dashed border-border bg-card p-3"
    >
      <span className="text-sm text-muted-foreground">Try a sample person:</span>
      {PERSONAS.map((persona) => (
        <Button
          key={persona.id}
          type="button"
          size="sm"
          variant={activePersona === persona.id ? "default" : "outline"}
          onClick={() => onLoad(persona.id)}
        >
          Load {persona.label}
        </Button>
      ))}
    </div>
  );
}

export { DemoSwitch, PersonaButtons };
