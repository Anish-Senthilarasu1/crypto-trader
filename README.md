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

### Option 1: Run Everything Locally (Recommended for Development)

1. **Clone and setup environment**:
   ```bash
   cd aurora-trader
   cp .env.example .env
   # Edit .env (API keys optional - works with synthetic data)
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the API** (Terminal 1):
   ```bash
   python -m backend.main
   # API runs at http://localhost:8000
   ```

4. **Start the Worker** (Terminal 2):
   ```bash
   # For single run (testing):
   python -m backend.worker

   # For continuous trading:
   # Edit .env: WORKER_ENABLED=true
   python -m backend.worker
   ```

5. **Start the UI** (Terminal 3):
   ```bash
   cd ui
   npm install
   npm run dev
   # UI runs at http://localhost:3000
   ```

6. **Open the Dashboard**:
   - Go to http://localhost:3000
   - View Dashboard, Live Trading, and Trades pages
   - Use kill switch to halt trading

### Option 2: Docker Deployment

```bash
docker compose up
```

Services:
- API: http://localhost:8000
- UI: http://localhost:3000
- Worker: Background scheduler

### Option 3: Run Just the Paper Trading (No UI)

```bash
# Install dependencies
pip install -r requirements.txt

# Run worker once
python -m backend.worker

# View results in database
sqlite3 data/aurora_trader.db "SELECT * FROM trades;"
```

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
| `/api/metrics` | GET | Trading performance metrics |
| `/api/metrics/positions` | GET | Current open positions |
| `/api/metrics/trades` | GET | Closed trade history |
| `/api/metrics/equity` | GET | Equity curve data |
| `/api/status` | GET | System status & daily P&L |
| `/api/halt` | POST | Emergency kill switch |
| `/api/resume` | POST | Deactivate kill switch |

## UI Dashboard

Access the web UI at http://localhost:3000

### Pages

1. **Dashboard** (`/`)
   - Equity curve chart (1 week view)
   - Current equity display
   - Total P&L ($ and %)
   - Win rate and trade count
   - Max drawdown metric
   - Auto-refresh every 30s

2. **Live Trading** (`/live`)
   - Worker status indicator
   - Kill switch controls
   - Daily P&L monitoring
   - Open positions table
   - Entry/exit prices
   - Unrealized P&L
   - Symbol whitelist
   - Auto-refresh every 5s

3. **Trades** (`/trades`)
   - All closed trades table
   - Filter by wins/losses
   - Entry/exit details
   - P&L per trade
   - Trade statistics
   - Auto-refresh every 10s

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

## How It Works

1. **Worker** fetches market data every 5 minutes (configurable)
2. **Strategy** analyzes candles for entry/exit signals
3. **Risk Manager** validates orders against limits
4. **Broker** simulates order execution (paper trading)
5. **Database** stores all orders, fills, and trades
6. **API** exposes metrics and controls
7. **UI** displays real-time performance

## Synthetic Data Mode

Without API keys, the system uses **synthetic data** for testing:
- Generates realistic OHLCV candles
- Simulates market volatility
- Perfect for strategy development
- No external API calls required

## Changelog

### [0.1.0] - 2025-10-29
#### Added
- Complete paper trading system
- FastAPI backend with metrics/control endpoints
- Live worker with APScheduler
- Momentum & mean-reversion strategies
- ATR-based risk management
- SQLite database for trade history
- Next.js UI dashboard
- Real-time position monitoring
- Kill switch functionality
- Docker deployment support
- Synthetic data mode
- 65 tests (all passing)

## License

MIT

## Support

For issues or questions, please open a GitHub issue.
