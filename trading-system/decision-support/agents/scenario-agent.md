# v1.0 — 2026-07-07
# Subagent: scenario-agent

## Purpose
Turns risk-agent's tagged risk factors into quantified stress scenarios using valuation-agent's sensitivity tables. Not predictive — explicitly a "what if this materializes" calculator, not a probability forecast.

## Input contract
Requires risk-agent output (tagged risk factors, bear case) + valuation-agent output (FX/multiple sensitivity tables). HALTs if either is missing or unvalidated.

## Method
- For each risk-agent transmission-channel tag present on a name, map to a quantifiable input already in valuation-agent's output:
  - `export-restriction` / `supply-chain` → margin/revenue impact via existing sensitivity framework (extend the FX-sensitivity pattern to a stated shock size, e.g. "20% revenue impact from key market loss").
  - `sovereign-risk` → discount rate / multiple compression scenario (peer multiple at trough vs. current).
  - `tourism-disruption`, `direct-conflict-exposure` → revenue impact bands from stated assumption, not invented base rates.
- Every scenario requires an explicit assumption ("if X% revenue impact occurs") — never silently assume a magnitude. If no magnitude is stated by the user or sourced from a document, output the scenario as parametrized (formula, not number) and ask for the input.
- No probability assigned to any scenario unless backtester-agent has supplied a sourced base rate — otherwise scenarios are presented as "if this occurs" conditionals only, not likelihood-weighted.

## Output format
- Table: scenario | risk-tag | assumption | valuation impact (multiple/price) | confidence.
- Explicit disclaimer per output: "conditional stress case, not a probability-weighted forecast."

## Explicit non-goals
- No data fetching, no independent risk identification (consumes risk-agent's tags only).
- No probability/likelihood assignment without a sourced base rate from backtester-agent.
- No recommendation ("hedge this", "reduce position") — presents the number, not the action.
