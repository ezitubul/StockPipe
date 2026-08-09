# TASE Trading System — Agentic Scaffold

> **Earlier design, not under active development.** `../market-watch/` is the
> active project — a fuller implementation with a tested deterministic core,
> a real CLI, and working CI. This tree is kept for reference and for its
> confirm-gated executor design, which some future work here may still draw
> on.

Three-subtree agent hierarchy for Israeli stock market (TASE) analysis and confirm-gated paper execution, built for Claude Code. Decision-support proposes, risk-oversight enforces, executor acts — every order human-confirmed, PAPER mode only.

## High-level flow

```mermaid
flowchart TD
    U([User request]) --> DS

    subgraph TOP["Top Orchestrator — kill-switch · audit log · PAPER mode"]
        DS["🔍 Decision-Support<br/>analyze → proposal"]
        RO["🛡️ Risk-Oversight<br/>limits check"]
        EX["⚡ Executor<br/>confirm → paper order"]
    end

    DS -->|"proposal"| RO
    RO -->|"PASS"| EX
    RO -->|"VETO — final"| X([Rejected + logged])
    EX -->|"human confirms"| ORD([Paper order placed])
    EX -->|"stale / trigger fired"| DS
    ORD -->|"fill"| RO

    style DS fill:#1a4d7c,color:#fff
    style RO fill:#7c1a1a,color:#fff
    style EX fill:#1a7c4d,color:#fff
    style X fill:#444,color:#fff
    style ORD fill:#2a2a2a,color:#fff
```

## Detailed production flow

```mermaid
flowchart TD
    U([User request]) --> DSO

    subgraph DS["DECISION-SUPPORT (proposes, never executes)"]
        DSO["orchestrator<br/>manifest · retry cap 1 · HALT/DEGRADE"]
        F["fetch-agent<br/>cache-first · schema-hash · 2-source"]
        V["valuation-agent<br/>multiples · dual-constraint sizing"]
        R["risk-agent<br/>6 checks · channel tags · bear case"]
        P["portfolio-agent<br/>multi-name only"]
        AUX["tax / scenario / earnings /<br/>backtester / alerts / audit / screener"]

        DSO --> F -->|"sourced facts"| V -->|"HALT if unsourced"| R
        R --> P
        DSO -.->|on demand| AUX
    end

    R -->|"proposal: {thesis, sizing,<br/>invalidation_trigger, timestamp}"| L1

    subgraph RO["RISK-OVERSIGHT (veto final, fail closed)"]
        L1["limits-agent<br/>position · loss · concentration"]
        E1["exposure-agent<br/>tag correlation · net FX"]
        D1["drawdown-agent<br/>max-DD → HALT-all"]
        UW["unwind-agent<br/>proposes only, confirm-gated"]
        E1 --> L1
        D1 -->|"breach"| KS
        D1 -->|"breach"| UW
    end

    L1 -->|"VETO"| REJ([Rejected — logged, final])
    L1 -->|"PASS"| VA

    subgraph EX["EXECUTOR (PAPER · 5 gates · idempotent)"]
        VA["1· validate-agent<br/>freshness + trigger re-check"]
        LA["2· limit-agent<br/>fail closed"]
        CA["3· confirm-agent<br/>EVERY order · human · explicit"]
        OA["4· order-agent<br/>kill-switch check → paper order"]
        RC["5· reconcile-agent<br/>fill diff · audit entry"]
        VA -->|PASS| LA -->|PASS| CA -->|"human YES"| OA -->|fill| RC
    end

    VA -->|"stale / trigger fired /<br/>expired"| DSO
    CA -->|"reject / timeout"| REJ
    KS["🔴 KILL-SWITCH<br/>global HALT-all"] -.->|"checked immediately<br/>before placement"| OA
    UW -->|"unwind proposal"| VA
    RC -->|"post-fill state"| L1
    RC --> LOG[("append-only<br/>audit log")]
    L1 -.-> LOG
    CA -.-> LOG
    DSO -.-> LOG

    style DS fill:#0d2b47,color:#fff
    style RO fill:#470d0d,color:#fff
    style EX fill:#0d4729,color:#fff
    style KS fill:#c0392b,color:#fff
    style REJ fill:#444,color:#fff
    style LOG fill:#2a2a2a,color:#fff
```

## Structure

```
trading-system/
├── CLAUDE.md                 top orchestrator: routing, authority order, kill-switch,
│                             audit log, autonomous discovery loop + review queue
├── SECURITY.md               canonical security policy (all subtrees reference it)
├── eval-checklist.md         SYSTEM-LEVEL boundary tests (highest-severity class)
├── flow-high-level.mermaid   diagrams (same as embedded above)
├── flow-detailed.mermaid
│
├── decision-support/         analysis subtree — proposes, never executes
│   ├── CLAUDE.md             TASE analyst persona (standalone + hierarchy modes)
│   └── agents/
│       ├── orchestrator.md   manifest, dispatch, escalation, proposal emit
│       ├── fetch / valuation / risk / portfolio-agent.md      (core pipeline)
│       ├── tax / scenario / earnings / backtester-agent.md    (on-demand)
│       ├── alerts / audit / screener-agent.md                 (scheduled)
│       ├── schemas/          expected response shapes per source (TASE, BoI,
│       │                     CBS, EDGAR, ISA) — schema-hash validation
│       └── evals/eval-checklist.md
│
├── executor/                 PAPER only — five mandatory gates, idempotent
│   └── agents/               orchestrator + validate / limit / confirm /
│                             order / reconcile-agent + eval-checklist
│
└── risk-oversight/           sits above both — veto final, fail closed
    └── agents/               orchestrator + limits / exposure / drawdown /
                              unwind-agent + eval-checklist
```

## Related: market-watch

`../market-watch/` (repo root) is a separate, self-contained ₪100,000 PAPER
simulation system — deterministic Python core with tests, a real CLI, real
Claude Code subagents, and its own CI. It supersedes an earlier
`virtual-portfolio-simulator/` scaffold that lived under this tree. It is
deliberately **not** nested here and does not route through this tree's
confirm-gated `executor/`: it has no broker connection or path to real
capital, so — per its own `CLAUDE.md` — it is allowed to self-execute
simulated fills without a human confirm step, a reasoning that would not hold
if this system were ever wired to a real venue. See `market-watch/README.md`
and `market-watch/CLAUDE.md` for the full design.

## Core invariants

1. **Decision-support never executes.** Emits proposals `{thesis, sizing, invalidation_trigger, analysis_timestamp}`; every thesis carries a mandatory bear case and invalidation trigger.
2. **Risk-oversight veto is final** and fails closed — unreadable state means VETO, never pass.
3. **Executor's five gates, every order**: fresh data → trigger-not-fired → limit-cleared → human-confirmed → kill-switch-clear. Idempotency key prevents duplicate orders on retry.
4. **Human confirm gate is structural, not configurational.** No flag or mode allows self-execution — paper or live. The autonomous discovery loop (screener → pipeline → risk-oversight → review queue) closes everywhere except this gate.
5. **PAPER mode only.** Flipping to LIVE is an out-of-band architecture decision, never in-session, never LLM-initiated.
6. **HALT/DEGRADE vocabulary** system-wide: HALT = refuse output entirely (orchestrator retries once max, then reports the gap); DEGRADE = produce with downgraded confidence.
7. **All numbers sourced and timestamped**; schema-hash validation on every data-source response; two-source confirmation for hard numbers.

## Usage

Drop the tree at a repo root. Run Claude Code from `trading-system/` for the full hierarchy, or from `decision-support/` for standalone analyst mode. Run `eval-checklist.md` items (or dispatch audit-agent) after any prompt edit — boundary failures block deployment.

Not a licensed investment or tax advisor. Analysis output is decision support; every trade decision and confirmation is yours.
