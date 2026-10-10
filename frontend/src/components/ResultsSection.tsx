import type { ReactNode } from "react";

interface ResultsSectionProps {
  id: string;
  title: string;
  children: ReactNode;
}

/** A titled section on the Results page. */
function ResultsSection({ id, title, children }: ResultsSectionProps) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <h3 id={id} className="text-xl font-semibold text-foreground">
        {title}
      </h3>
      {children}
    </section>
  );
}

/** Gentle grey text for an empty section. */
function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="text-base text-muted-foreground">{children}</p>;
}

export { ResultsSection, EmptyNote };
