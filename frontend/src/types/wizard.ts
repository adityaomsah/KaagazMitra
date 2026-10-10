// Frontend-only wizard types. These describe transient UI state for the
// five-step flow and are NOT part of the backend API contract in api.ts.

import type { DocumentType } from "@/types/api";

/** Life events captured in Step 2, keyed to CheckRequest.life_events. */
export type LifeEvent =
  | "name_change"
  | "address_change"
  | "dob_difference";

/** A document the user added in Step 3, before any server-side extraction. */
export interface UploadedDocument {
  id: string;
  file: File;
  /** Object URL used for the on-screen image preview. */
  previewUrl: string;
  /** Empty string until the user picks a type from the dropdown. */
  documentType: DocumentType | "";
}

/** The single wizard answer object kept in App.tsx. */
export interface WizardAnswers {
  service_id: string | null;
  life_events: LifeEvent[];
  documents: UploadedDocument[];
  consent: boolean;
}

export const TOTAL_STEPS = 5;

export const initialAnswers: WizardAnswers = {
  service_id: null,
  life_events: [],
  documents: [],
  consent: false,
};
