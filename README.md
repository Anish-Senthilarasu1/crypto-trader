# Aurora Trader

Production-ready **paper trading system** with web UI for cryptocurrencies and stocks.

## Features

- 🔄 **Multi-Market Support**: Trade crypto (Coinbase) or stocks (Alpaca) via unified interfaces
- 📊 **Built-in Strategies**: Momentum breakout and mean-reversion with VWAP
- 🛡️ **Risk Management**: ATR-based position sizing, daily loss limits, exposure caps
- 📈 **Backtesting Engine**: Vectorized backtests with walk-forward analysis
- 🌐 **Modern Web UI**: Real-time dashboard with charts and controls
- ⚡ **Live Paper Trading**: Automated execution in sandbox environments
- 🚨 **Kill Switch**: Instant halt capability for risk management
- 📱 **Alerts**: Optional Slack/email notifications

## Architecture

```
aurora-trader/
├── backend/           # FastAPI REST API + Trading Engine
│   ├── api/          # REST endpoints
│   ├── engine/       # Core trading logic
│   │   ├── data_feed/    # Market data adapters
│   │   ├── broker/       # Order execution adapters
│   │   ├── signals/      # Strategy implementations
│   │   ├── risk/         # Position sizing & limits
│   │   ├── backtest/     # Backtesting framework
│   │   └── store/        # Database layer
│   └── tests/        # pytest suite
├── ui/               # Next.js dashboard
├── ops/              # Docker & deployment scripts
└── configs/          # Strategy configurations
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone and setup environment**:
   ```bash
   git clone <repo-url>
   cd aurora-trader
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the API**:
   ```bash
   python -m backend.main
   ```

4. **Verify health**:
   ```bash
   curl http://localhost:8000/health
   ```

### Docker Deployment

```bash
docker compose up
```

Services:
- API: http://localhost:8000
- UI: http://localhost:3000
- Worker: Background scheduler

## Configuration

Edit `.env` to configure:

### Market Selection
```bash
USE_MARKET=crypto           # or 'stocks'
DEFAULT_SYMBOL=BTC-USD      # or stock ticker
TIMEFRAME=5m
```

### Risk Parameters
```bash
RISK_PER_TRADE=0.005        # 0.5% per trade
MAX_DAILY_LOSS=0.02         # 2% daily kill threshold
MAX_PORTFOLIO_EXPOSURE=0.4  # 40% max exposure
SYMBOL_WHITELIST=BTC-USD,ETH-USD
```

### API Keys

**Coinbase Advanced Trade (Sandbox)**:
```bash
COINBASE_API_KEY=your_key
COINBASE_API_SECRET=your_secret
COINBASE_PASSPHRASE=your_passphrase
COINBASE_SANDBOX=1
```

**Alpaca Paper Trading**:
```bash
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Performance metrics |
| `/config` | GET/PUT | Strategy parameters |
| `/signals/preview` | GET | Preview signals |
| `/trade/paper` | POST | Start/stop live trading |
| `/halt` | POST | Emergency kill switch |

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test
pytest backend/tests/test_strategies.py -v
```

## Development Workflow

1. **Pre-commit hooks** (auto-formatting):
   ```bash
   pre-commit install
   ```

2. **Code style** (black + isort):
   ```bash
   black backend/
   isort backend/
   ```

3. **Type checking**:
   ```bash
   mypy backend/
   ```

## Strategies

### 1. Momentum Breakout
- Entry: Price breaks 20-period high
- Stop: 2x ATR below entry
- Trailing: ATR-based trailing stop

### 2. Mean Reversion
- Entry: Price < VWAP + Bollinger confirmation
- Exit: Price > VWAP or stop loss

### Sentiment Overlay (Optional)
Scale position size by sentiment score in [-1, 1].

## Security

See [SECURITY.md](SECURITY.md) for:
- API key management
- Kill switch procedures
- Audit logging
- Incident response

## Changelog

### [0.1.0] - 2025-10-29
#### Added
- Project scaffold with FastAPI backend
- Health check endpoint
- Docker configuration
- Pre-commit hooks
- Basic project structure

## License

MIT

## Support

For issues or questions, please open a GitHub issue.
