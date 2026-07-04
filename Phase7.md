### Phase 7 — Ecosystem Integration Simulators (ULI/OCEN/AA)

**Instruction to IDE agent:**

Build mock connector modules simulating: (a) an AA consent-flow handshake (issue/revoke consent, expiry handling — already partially built in Phase 5's consent gate, this phase adds the initiating "request consent" flow and a simple consent UI screen), (b) a ULI-style standardized data-fetch response format, (c) an OCEN-style loan-service-provider signal exchange stub. These should be clearly marked as simulators (mock external system, deterministic canned \+ config-driven responses) but structured so a real integration later is a matter of implementing the same interface against a real endpoint. Expose status via the `/ecosystem/*` endpoints and the "Ecosystem Status" frontend screen. **Definition of Done:** Demo can show a consent request → grant → data-gated score unlock flow end-to-end; ecosystem status screen reflects mock connector health.

