import { CircleCheck, CircleHelp, CircleX, TriangleAlert, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MismatchStatus } from "@/types/api";

interface ChipStyle {
  label: string;
  icon: LucideIcon;
  className: string;
}

// Colour is never the only signal: each chip also has an icon and text.
const STYLES: Record<MismatchStatus, ChipStyle> = {
  MATCH: {
    label: "Matches",
    icon: CircleCheck,
    className: "border-green-300 bg-green-50 text-green-800",
  },
  POSSIBLE_VARIANT: {
    label: "Possibly the same",
    icon: TriangleAlert,
    className: "border-yellow-300 bg-yellow-50 text-yellow-800",
  },
  DIFFERENCE: {
    label: "Different",
    icon: CircleX,
    className: "border-red-300 bg-red-50 text-red-800",
  },
  UNKNOWN: {
    label: "Couldn't read",
    icon: CircleHelp,
    className: "border-gray-300 bg-gray-100 text-gray-700",
  },
};

interface StatusChipProps {
  status: MismatchStatus;
  className?: string;
}

/** Coloured pill describing how a field compared across documents. */
function StatusChip({ status, className }: StatusChipProps) {
  const style = STYLES[status] ?? STYLES.UNKNOWN;
  const Icon = style.icon;
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold",
        style.className,
        className,
      )}
    >
      <Icon className="size-4" aria-hidden="true" />
      {style.label}
    </span>
  );
}

export { StatusChip };
