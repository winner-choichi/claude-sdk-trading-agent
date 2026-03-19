# Trading Agent Plan

This document turns the current repository into a clear delivery plan. It is based on the code and docs already present in `trading_agent/`, while also outlining the work needed to move from a local prototype to a safely operated autonomous trading system.

## Goals

- Build a reliable paper-trading agent before any live deployment
- Keep human approval in the loop until confidence and risk controls prove stable
- Create a repeatable cycle of strategy generation, backtesting, evaluation, and rollout
- Make operations observable through Slack reports, alerts, and emergency controls

## Product Scope

```mermaid
mindmap
  root((Trading Agent))
    Execution
      Alpaca paper trading
      Order lifecycle tracking
      Safety limits
    Intelligence
      Strategy generation
      Confidence scoring
      Meta-learning
      Parameter tuning
    Validation
      Historical backtests
      Walk-forward checks
      Performance metrics
    Operations
      Slack approvals
      Daily reporting
      Pause and resume controls
      Setup verification
    Persistence
      Trade history
      Strategy state
      Performance snapshots
      Configurable storage
```

## System Architecture

```mermaid
flowchart TD
    Slack[Slack Commands and Alerts]
    Main[main.py Orchestrator]
    Agent[Trading Agent Core]
    Hooks[Approval and Risk Hooks]
    Tools[Trading and Analysis Tools]
    Backtest[Backtest Engine]
    Storage[SQLite and Models]
    Brokers[Alpaca APIs]
    Docs[Setup and Ops Docs]

    Slack --> Main
    Main --> Agent
    Agent --> Hooks
    Agent --> Tools
    Agent --> Backtest
    Tools --> Brokers
    Hooks --> Storage
    Backtest --> Storage
    Agent --> Storage
    Main --> Docs
```

## Trading Decision Flow

```mermaid
flowchart LR
    A[Market Check] --> B[Signal or Opportunity]
    B --> C[Claude-driven Analysis]
    C --> D[Confidence and Risk Scoring]
    D --> E{Above auto-execute threshold?}
    E -- Yes --> F[Run Hook Validation]
    E -- No --> G[Request Slack Approval]
    F --> H{Within limits?}
    H -- Yes --> I[Submit Order]
    H -- No --> G
    G --> J{Approved?}
    J -- Yes --> I
    J -- No --> K[Cancel Trade]
    I --> L[Persist Trade and Metrics]
    L --> M[Report to Slack]
```

## Delivery Phases

```mermaid
timeline
    title Delivery Roadmap
    Phase 1 : Environment setup and config validation
            : Alpaca paper trading connectivity
            : Slack bot wiring
    Phase 2 : Approval hooks and operational reporting
            : Portfolio visibility
            : Emergency pause and resume
    Phase 3 : Backtesting and optimization loop
            : Historical replay
            : Metrics and validation
    Phase 4 : Self-tuning strategy evolution
            : Confidence calibration
            : Parameter adjustment
    Phase 5 : Production hardening
            : Monitoring
            : Deployment
            : Live-trading readiness review
```

## Phase Breakdown

### Phase 1. Baseline readiness

- Validate config loading, environment variables, and startup behavior
- Confirm Alpaca paper trading connectivity
- Verify database creation and storage models
- Run setup verification and document any missing local prerequisites

### Phase 2. Safe operations

- Make Slack alerts and interactive approvals dependable
- Ensure risk limits gate execution consistently
- Add clear operational status, portfolio, and health reporting
- Keep emergency stop paths simple and testable

### Phase 3. Validation engine

- Strengthen historical data ingestion and replay
- Produce consistent backtest outputs and performance summaries
- Add walk-forward validation and comparison reporting
- Define clear promotion criteria from backtest to paper trading

### Phase 4. Adaptive intelligence

- Improve confidence calibration against realized outcomes
- Tune thresholds and position sizing based on rolling performance
- Track strategy variants and retire underperforming behavior
- Build a measured evolution cadence rather than constant churn

### Phase 5. Production hardening

- Add deployment and runtime monitoring guidance
- Improve failure handling for network, broker, and Slack outages
- Define audit trails for decisions and approvals
- Create a checklist for any future live-trading transition

## Milestones and Exit Criteria

| Milestone | Exit Criteria |
| --- | --- |
| Paper trading ready | Config loads cleanly, broker connection works, trades can be simulated safely |
| Ops ready | Slack alerts, approvals, reporting, and pause flow are verified |
| Backtest ready | Historical runs are reproducible and performance metrics are trustworthy |
| Adaptive ready | Threshold tuning is measurable and bounded by risk constraints |
| Deployment ready | Monitoring, documentation, and recovery procedures are in place |

## Risks to Manage

- Overconfident autonomous execution before validation is mature
- Incomplete market-data coverage during backtests
- Slack or broker outages interrupting approvals or reporting
- Strategy drift that improves recent results but weakens robustness
- Configuration mistakes leaking secrets or enabling live trading too early

## Recommended Near-Term Priorities

1. Keep the system in paper trading mode and verify the current setup end to end.
2. Exercise the approval flow and Slack reporting until the operator experience feels predictable.
3. Tighten the backtesting loop so strategy changes always have measurable evidence behind them.
4. Only then widen autonomous execution thresholds and consider deployment hardening.
