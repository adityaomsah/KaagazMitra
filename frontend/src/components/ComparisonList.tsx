import { StatusChip } from "@/components/StatusChip";
import { EmptyNote } from "@/components/ResultsSection";
import { fieldLabel } from "@/lib/contractGaps";
import { documentLabelById } from "@/lib/labels";
import type { Document, Mismatch } from "@/types/api";

interface ComparisonListProps {
  mismatches: Mismatch[];
  documents: Document[];
}

/** "What we compared": one row per field with values per document + StatusChip. */
function ComparisonList({ mismatches, documents }: ComparisonListProps) {
  if (mismatches.length === 0) {
    return <EmptyNote>There were no details to compare across your documents.</EmptyNote>;
  }
  return (
    <ul className="flex flex-col gap-3">
      {mismatches.map((mismatch, i) => (
        <li
          key={`${mismatch.field}-${i}`}
          className="rounded-xl border-2 border-border bg-card p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-lg font-semibold text-foreground">
              {fieldLabel(mismatch.field)}
            </span>
            <StatusChip status={mismatch.status} />
          </div>
          <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[auto_1fr]">
            {Object.entries(mismatch.values).map(([docId, value]) => (
              <div key={docId} className="contents">
                <dt className="text-sm text-muted-foreground">
                  {documentLabelById(documents, docId)}
                </dt>
                <dd className="text-base text-foreground">
                  {value || <span className="text-muted-foreground">Not readable</span>}
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-sm text-muted-foreground">{mismatch.explanation}</p>
        </li>
      ))}
    </ul>
  );
}

export { ComparisonList };
