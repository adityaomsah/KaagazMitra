// Frontend-only shape for a demo persona. Not part of the API contract.

import type { CheckResponse, Document } from "@/types/api";
import type { LifeEvent } from "@/types/wizard";

export type PersonaId = "anita" | "rahim" | "ramesh";

export interface Persona {
  id: PersonaId;
  /** Button text: "Load <label>". */
  label: string;
  service_id: string;
  life_events: LifeEvent[];
  /** Already-extracted documents (what /api/extract would return). */
  documents: Document[];
  /** What /api/check would return for these documents. */
  check: CheckResponse;
}
