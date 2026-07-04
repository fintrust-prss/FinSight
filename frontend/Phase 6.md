### Phase 6 — Frontend Application

**Instruction to IDE agent:**

Build the five screens from Section 10 against the Phase 5 API contract, using React Query (or SWR) for data fetching with proper loading/error/empty states everywhere. Build the Health Card radar chart, gauge, and "why this score" panel using Recharts. Implement tier color-coding meeting WCAG AA contrast. Add Vitest \+ React Testing Library component tests for the Health Card and Dashboard, and one Playwright e2e happy-path test. No direct cloud SDK usage in frontend code — all data via the backend API only. **Definition of Done:** Full user journey (login → dashboard → MSME health card → explanation → data source explorer) works against the live backend; component \+ e2e tests pass in CI.
