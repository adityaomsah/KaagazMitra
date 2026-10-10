import { cn } from "@/lib/utils";

interface ProgressBarProps {
  /** Current step, 1-based (e.g. 3 for "Step 3 of 5"). */
  current: number;
  /** Total number of steps. Defaults to 5. */
  total?: number;
  className?: string;
}

/**
 * Accessible progress indicator for the wizard.
 * Announces "Step X of Y" via text plus an ARIA progressbar for the fill level.
 */
function ProgressBar({ current, total = 5, className }: ProgressBarProps) {
  const safeTotal = total > 0 ? total : 1;
  const clampedCurrent = Math.min(Math.max(current, 1), safeTotal);
  const percent = Math.round((clampedCurrent / safeTotal) * 100);

  return (
    <div className={cn("w-full", className)} data-slot="progress-bar">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-sm font-semibold text-foreground">
          Step {clampedCurrent} of {safeTotal}
        </span>
        <span className="text-xs font-medium text-muted-foreground">
          {percent}%
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={clampedCurrent}
        aria-valuemin={1}
        aria-valuemax={safeTotal}
        aria-label={`Step ${clampedCurrent} of ${safeTotal}`}
        className="h-2.5 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export { ProgressBar };
