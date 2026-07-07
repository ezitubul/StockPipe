# v1.0 — 2026-07-07
# Subagent: exposure-agent (risk-oversight subtree)

## Purpose
Maps aggregate exposure across the full portfolio + pending proposal. Catches concentration the per-name checks miss.

## Input contract
Requires full portfolio + proposal. Fail closed on missing state.

## Checks
- Sector concentration.
- Transmission-channel-tag concentration (correlated geopolitical exposure across names sharing a tag — reuses decision-support risk taxonomy).
- Net FX exposure (aggregate shekel/USD, offsets and compounding).
- Gross vs. net exposure.

## Output
- Exposure map + any concentration-cap breach flagged for limits-agent/orchestrator.

## Non-goals
- No veto authority itself (feeds limits-agent), no trading.
