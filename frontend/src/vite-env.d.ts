/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" (or "true") = frontend mock mode: extract()/check() use src/mock, no backend. */
  readonly VITE_USE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
