// Central API layer for KaagazMitra.
// All frontend network access goes through this file (see AGENTS.md).
//
// USE_MOCK=true returns bundled JSON fixtures after a short delay so the UI
// works without the FastAPI backend or Gemini. Flip to false to hit /api/...
// (Vite proxies /api to http://localhost:8000).

import type {
  CheckRequest,
  CheckResponse,
  Document,
  HealthResponse,
} from "@/types/api";

import servicesData from "@/mock/services.json";
import extractRahimData from "@/mock/extract_rahim.json";
import extractAnitaData from "@/mock/extract_anita.json";
import extractRameshData from "@/mock/extract_ramesh.json";
import checkRahimData from "@/mock/check_rahim.json";
import checkAnitaData from "@/mock/check_anita.json";
import checkRameshData from "@/mock/check_ramesh.json";

// TEMP: contract gap — `Service` is not defined in src/types/api.ts, so the
// frontend declares its own shape for the /api/services response. Remove this
// once the backend adds a `Service` model to schemas.py.
export interface Service {
  id: string;
  name: string;
  description: string;
  available: boolean;
}

// TEMP: contract gap — no request/response types exist in src/types/api.ts for
// the rejection-decoder, translator, or report endpoints. These are frontend
// placeholders; replace with the real backend schemas when available.
export interface DecodeRejectionRequest {
  text: string;
}

export interface DecodeRejectionResponse {
  plain_language: string;
  likely_reasons: string[];
  suggested_actions: string[];
  confidence: number;
}

export interface TranslateRequest {
  text: string;
  target_language: string;
}

export interface TranslateResponse {
  original_text: string;
  translated_text: string;
  target_language: string;
}

export interface ReportSection {
  heading: string;
  body: string;
}

export interface ReportRequest {
  service_id: string;
  check: CheckResponse;
}

export interface ReportResponse {
  service_id: string;
  generated_at: string;
  summary: string;
  sections: ReportSection[];
}

// Toggle mock mode. Keep true until the backend is reachable.
export const USE_MOCK = true;

const API_BASE = "/api";
const MOCK_DELAY_MS = 250;

function delay(ms: number = MOCK_DELAY_MS): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Mock scenario selection. Keyed off a person's name found in a filename or in
// the uploaded document ids/filenames.
type ScenarioKey = "rahim" | "anita" | "ramesh";

function detectScenario(haystack: string): ScenarioKey {
  const s = haystack.toLowerCase();
  if (s.includes("anita")) return "anita";
  if (s.includes("ramesh") || s.includes("रमेश")) return "ramesh";
  return "rahim";
}

// TEMP: contract gap — the `document_type` enum has no "land_record" value, so
// Ramesh's land record mock uses the generic "other" type (see
// src/mock/extract_ramesh.json). Also, `ExtractedField` has no
// `transliterated_value`, so the Devanagari name is stored with the original in
// `raw_value` ("रमेश कुमार") and the Latin form in `normalized_value`.
const EXTRACT_MOCKS: Record<ScenarioKey, Document[]> = {
  rahim: extractRahimData as Document[],
  anita: extractAnitaData as Document[],
  ramesh: extractRameshData as Document[],
};

const CHECK_MOCKS: Record<ScenarioKey, CheckResponse> = {
  rahim: checkRahimData as CheckResponse,
  anita: checkAnitaData as CheckResponse,
  ramesh: checkRameshData as CheckResponse,
};

const MOCK_SERVICES = servicesData as Service[];

// Minimal JSON fetch helper for the live (non-mock) path.
async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

const JSON_HEADERS: HeadersInit = { "Content-Type": "application/json" };

// GET /api/health — liveness probe used by the connection banner.
export async function getHealth(): Promise<HealthResponse> {
  if (USE_MOCK) {
    await delay();
    return { status: "ok", version: "0.1.0", use_mock: true };
  }
  return apiRequest<HealthResponse>("/health");
}

// GET /api/services — list of available government services.
export async function getServices(): Promise<Service[]> {
  if (USE_MOCK) {
    await delay();
    return MOCK_SERVICES.map((service) => ({ ...service }));
  }
  return apiRequest<Service[]>("/services");
}

// POST /api/extract — extract structured fields from one uploaded document.
// TEMP: contract gap — there is no `ExtractRequest`/`ExtractResponse` type; the
// frontend assumes a single-file upload returning Document[]. Adjust when the
// backend contract is defined.
export async function extract(file: File): Promise<Document[]> {
  if (USE_MOCK) {
    await delay();
    const scenario = detectScenario(file.name);
    return structuredClone(EXTRACT_MOCKS[scenario]);
  }
  const form = new FormData();
  form.append("file", file);
  return apiRequest<Document[]>("/extract", { method: "POST", body: form });
}

// POST /api/check — run document consistency + readiness analysis.
export async function check(request: CheckRequest): Promise<CheckResponse> {
  if (USE_MOCK) {
    await delay();
    const haystack = request.documents
      .map((doc) => `${doc.id} ${doc.filename}`)
      .join(" ");
    const scenario = detectScenario(haystack);
    return structuredClone(CHECK_MOCKS[scenario]);
  }
  return apiRequest<CheckResponse>("/check", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(request),
  });
}

// POST /api/decode-rejection — explain a rejection notice in plain language.
export async function decodeRejection(
  input: DecodeRejectionRequest,
): Promise<DecodeRejectionResponse> {
  if (USE_MOCK) {
    await delay();
    return {
      plain_language:
        "This is sample mock data. In mock mode we cannot decode a real rejection notice.",
      likely_reasons: [
        "Sample reason: a detail did not match across your documents.",
      ],
      suggested_actions: [
        "Sample action: re-check the details on your documents and try again.",
      ],
      confidence: 0,
    };
  }
  return apiRequest<DecodeRejectionResponse>("/decode-rejection", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(input),
  });
}

// POST /api/translate — translate guidance text into a target language.
export async function translate(
  input: TranslateRequest,
): Promise<TranslateResponse> {
  if (USE_MOCK) {
    await delay();
    return {
      original_text: input.text,
      translated_text: `[mock] ${input.text}`,
      target_language: input.target_language,
    };
  }
  return apiRequest<TranslateResponse>("/translate", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(input),
  });
}

// POST /api/report — build a shareable readiness summary from a check result.
export async function report(input: ReportRequest): Promise<ReportResponse> {
  if (USE_MOCK) {
    await delay();
    const { check } = input;
    const sections: ReportSection[] = [
      {
        heading: "Status",
        body: `Sample readiness status: ${check.readiness.status}.`,
      },
      {
        heading: "Next steps",
        body:
          check.readiness.next_steps.join(" ") ||
          "Sample: no next steps available.",
      },
    ];
    return {
      service_id: input.service_id,
      generated_at: new Date().toISOString(),
      summary: `Sample readiness summary for ${input.service_id}.`,
      sections,
    };
  }
  return apiRequest<ReportResponse>("/report", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(input),
  });
}


