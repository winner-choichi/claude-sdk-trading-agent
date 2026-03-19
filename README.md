# Claude SDK Trading Agent

An autonomous trading agent built with the Claude Agent SDK, Alpaca, and Slack. The project focuses on safe paper-trading workflows first, then adds approval hooks, reporting, backtesting, and self-tuning behavior for more autonomous operation.

## What is in this repository

- `trading_agent/`: the Python application, configuration templates, setup guides, and implementation docs
- `PLAN.md`: a product and delivery plan with Mermaid diagrams for architecture, workflow, and rollout phases

## Highlights

- Autonomous trading flow with approval hooks and risk limits
- Alpaca integration for orders and market data
- Slack bot support for alerts, commands, and trade approvals
- Backtesting and optimization support
- SQLite-based persistence layer
- Deployment-oriented packaging with a `Dockerfile`

## Repository Layout

```text
.
├── PLAN.md
├── README.md
└── trading_agent/
    ├── agent/
    ├── config/
    ├── docs/
    ├── hooks/
    ├── messaging/
    ├── storage/
    ├── tests/
    ├── tools/
    ├── Dockerfile
    ├── README.md
    ├── main.py
    ├── requirements.txt
    └── verify_setup.py
```

## Quick Start

1. Create a Python 3.11+ virtual environment.
2. Install dependencies from [`trading_agent/requirements.txt`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/requirements.txt).
3. Copy [`trading_agent/config/config.example.yaml`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/config/config.example.yaml) to `trading_agent/config/config.yaml`.
4. Fill in Alpaca credentials and optional Slack credentials.
5. Start in paper trading mode from the `trading_agent/` directory.

```bash
cd trading_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
python main.py
```

## Configuration Notes

- Default mode is `PAPER_TRADING`, which is the right place to start.
- Slack is optional, but most approval and monitoring flows assume it is configured.
- Local runtime data such as `config.yaml`, logs, SQLite data, and screenshots are intentionally gitignored.

## Documentation Map

- Product and rollout plan: [`PLAN.md`](/Users/choechiwon/toys/claudeAgentSDK/PLAN.md)
- App-specific guide: [`trading_agent/README.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/README.md)
- Quickstart: [`trading_agent/docs/setup/QUICKSTART.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/setup/QUICKSTART.md)
- Slack setup: [`trading_agent/docs/setup/slack_bot_setup.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/setup/slack_bot_setup.md)
- Approval flow: [`trading_agent/docs/APPROVAL_FLOW.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/APPROVAL_FLOW.md)
- Implementation status: [`trading_agent/docs/development/IMPLEMENTATION_STATUS.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/development/IMPLEMENTATION_STATUS.md)

## Current State

The repository already contains the application skeleton, trading tools, Slack messaging layer, storage layer, setup documents, and tests. The next step is to harden configuration, validate end-to-end setup, and iterate on the autonomous strategy and backtesting loop described in the plan.
