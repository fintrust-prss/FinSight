"""
Ecosystem Integration Simulators — Phase 7.

Modules:
  aa_simulator   — Account Aggregator consent-flow handshake
  uli_simulator  — ULI-style standardised data-fetch response formatter
  ocen_simulator — OCEN LSP signal-exchange stub

All simulators are deterministic (canned + config-driven) and clearly marked
as MOCK. The same interface contracts allow a real integration later by
swapping the implementation behind each function without touching callers.
"""
