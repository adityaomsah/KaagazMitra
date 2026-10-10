
# KaagazMitra — Project Instructions

## Project
AI-powered document consistency and application-readiness assistant for Indian citizens.

## Stack
- Frontend: React, Vite, TypeScript, Tailwind, shadcn/ui
- Backend: Python, FastAPI, Pydantic
- AI: Gemini Vision
- Matching: RapidFuzz and deterministic rules
- Service guidance: verified JSON rulebooks

## Architecture
- backend/app/schemas.py is the source of truth.
- frontend/src/types/api.ts must match backend schemas.
- All frontend API calls go through frontend/src/lib/api.ts.
- Vite proxies /api to localhost:8000.
- Backend application modules use flat files.

## Development
- Person 1 owns backend.
- Person 2 owns frontend and official-rule research.
- Use small, testable implementations.
- Run tests after each milestone.
- Never silently change shared API contracts.
- Keep USE_MOCK=1 functional without Gemini.

## Privacy and Safety
- Never commit API keys or real identity documents.
- Preserve original names and original scripts.
- Never silently remove name components.
- AI confidence is an estimate, not verified certainty.
- Users must review uncertain extracted fields.
- Obtain consent before sending images to cloud AI.
- Do not store uploaded documents permanently by default.
- Never invent government rules or correction procedures.
- Use verified source-linked rules only.
- Never guarantee application approval.

## UI/UX
- Mobile-first, accessible, low-literacy-friendly.
- Forest green #155E4B.
- Off-white #F8FAF7.
- Subtle saffron accents.
- Large buttons, readable text, plain language.
- Five steps: Service, Situation, Documents, Review, Guidance.
- Explain findings without alarming users.
