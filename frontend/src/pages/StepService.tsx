import { useEffect, useMemo, useState } from "react";
import {
  BookUser,
  Check,
  GraduationCap,
  Landmark,
  ScrollText,
  Store,
  Wheat,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { listServices } from "@/lib/api";
import type { ServiceRule } from "@/types/api";

/**
 * Step 1 — "What do you need help with?"
 *
 * A fixed DISPLAY catalog drives labels, descriptions and icons. Availability
 * is API-driven: a card is only selectable when listServices() returns a rule
 * whose `service` matches the card id. Services returned by the API that are
 * not in the catalog are shown as extra cards using their API-provided name.
 *
 * Demo mode keeps `passport_reissue` always available so the offline persona
 * demo works, and a fetch failure degrades gracefully (all cards "Coming soon"
 * except the demo service) instead of blocking the flow.
 */

// When true, the passport reissue card stays selectable even if the backend
// is unreachable, so the persona demo never gets stuck on Step 1.
const DEMO_MODE = true;
const DEMO_ALWAYS_AVAILABLE = "passport_reissue";

interface CatalogEntry {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

const CATALOG: CatalogEntry[] = [
  {
    id: "passport_reissue",
    label: "Passport reissue",
    description: "Fix a name, spelling or detail before reissuing your passport.",
    icon: BookUser,
  },
  {
    id: "bank_kyc",
    label: "Bank KYC",
    description: "Update or re-verify your bank account KYC details.",
    icon: Landmark,
  },
  {
    id: "nsp_scholarship",
    label: "Scholarship",
    description: "Apply for a scholarship and check your documents match.",
    icon: GraduationCap,
  },
  {
    id: "pm_kisan",
    label: "PM-KISAN (farmers)",
    description: "Farmer income support — keep your records consistent.",
    icon: Wheat,
  },
  {
    id: "udyam",
    label: "Business registration (Udyam)",
    description: "Register or update your Udyam / MSME business details.",
    icon: Store,
  },
];

// Icon used for services that come back from the API but are not in the catalog.
const FALLBACK_ICON: LucideIcon = ScrollText;

type LoadState = "loading" | "ready" | "error";

/** Present an API `service` id (e.g. "old_age_pension") as a readable label. */
function prettyServiceName(service: string): string {
  return service
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

interface CardModel {
  key: string;
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  available: boolean;
}

interface StepServiceProps {
  selected: string | null;
  onSelect: (serviceId: string) => void;
  onBack: () => void;
  onContinue: () => void;
}

function StepService({ selected, onSelect, onBack, onContinue }: StepServiceProps) {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [apiServices, setApiServices] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    listServices()
      .then((rules: ServiceRule[]) => {
        if (!active) return;
        setApiServices(rules.map((rule) => rule.service));
        setLoadState("ready");
      })
      .catch(() => {
        if (!active) return;
        setApiServices([]);
        setLoadState("error");
      });
    return () => {
      active = false;
    };
  }, []);

  // Build the ordered list of cards: catalog entries first, then any extra
  // services the API returned that are not already represented.
  const cards = useMemo<CardModel[]>(() => {
    const availableSet = new Set(apiServices);
    const catalogCards: CardModel[] = CATALOG.map((entry) => ({
      key: entry.id,
      id: entry.id,
      label: entry.label,
      description: entry.description,
      icon: entry.icon,
      available:
        availableSet.has(entry.id) ||
        (DEMO_MODE && entry.id === DEMO_ALWAYS_AVAILABLE),
    }));

    const catalogIds = new Set(CATALOG.map((entry) => entry.id));
    const extraCards: CardModel[] = apiServices
      .filter((service) => !catalogIds.has(service))
      .map((service) => ({
        key: service,
        id: service,
        label: prettyServiceName(service),
        description: "Available service from our verified rulebook.",
        icon: FALLBACK_ICON,
        available: true,
      }));

    return [...catalogCards, ...extraCards];
  }, [apiServices]);

  const reachabilityNote =
    loadState === "error"
      ? "We can't reach the server right now. You can still continue with the demo option."
      : null;

  return (
    <section aria-labelledby="step-service-heading" className="flex flex-col gap-6">
      <header className="space-y-1">
        <h2
          id="step-service-heading"
          className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
        >
          What do you need help with?
        </h2>
        <p className="text-base text-muted-foreground">
          Pick the service you are applying for. We'll check your documents
          against its rules.
        </p>
      </header>

      {reachabilityNote && (
        <p
          role="status"
          className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground"
        >
          {reachabilityNote}
        </p>
      )}

      <ul
        role="radiogroup"
        aria-label="Available services"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2"
      >
        {cards.map((card) => {
          const isSelected = selected === card.id;
          const Icon = card.icon;
          return (
            <li key={card.key}>
              <button
                type="button"
                role="radio"
                aria-checked={isSelected}
                aria-disabled={!card.available}
                disabled={!card.available}
                onClick={() => card.available && onSelect(card.id)}
                className={cn(
                  "relative flex h-full w-full flex-col items-start gap-3 rounded-xl border-2 bg-card p-5 text-left transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  isSelected
                    ? "border-primary bg-accent/30"
                    : "border-border hover:border-primary/50",
                  !card.available && "cursor-not-allowed opacity-60",
                )}
              >
                <span
                  className={cn(
                    "flex size-12 items-center justify-center rounded-lg",
                    isSelected
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-primary",
                  )}
                >
                  <Icon className="size-6" aria-hidden="true" />
                </span>

                <span className="flex w-full items-center justify-between gap-2">
                  <span className="text-lg font-semibold text-foreground">
                    {card.label}
                  </span>
                  {isSelected && (
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <Check className="size-4" aria-hidden="true" />
                      <span className="sr-only">Selected</span>
                    </span>
                  )}
                </span>

                <span className="text-sm text-muted-foreground">
                  {card.description}
                </span>

                {!card.available && (
                  <span className="absolute right-4 top-4 rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                    Coming soon
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="mt-2 flex items-center justify-between gap-4">
        <Button type="button" variant="outline" size="lg" onClick={onBack} disabled>
          Back
        </Button>
        <Button
          type="button"
          size="lg"
          onClick={onContinue}
          disabled={!selected}
        >
          Continue
        </Button>
      </div>
    </section>
  );
}

export { StepService };
