// Demo personas used by the "Demo" switch and by frontend mock mode
// (VITE_USE_MOCK=1). All data is fictional sample data.

import { anita } from "@/mock/anita";
import { rahim } from "@/mock/rahim";
import { ramesh } from "@/mock/ramesh";
import type { Persona, PersonaId } from "@/mock/types";

export type { Persona, PersonaId } from "@/mock/types";

/** Display order for the "Load ..." buttons. */
export const PERSONAS: Persona[] = [anita, rahim, ramesh];

/** Persona used by mock mode when no demo persona was loaded. */
export const DEFAULT_PERSONA_ID: PersonaId = "rahim";

export function getPersona(id: PersonaId): Persona {
  return PERSONAS.find((p) => p.id === id) ?? rahim;
}
