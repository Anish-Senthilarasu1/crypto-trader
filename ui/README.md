# Aurora Trader UI

Next.js dashboard for Aurora Trader paper trading system.

## Features

- **Dashboard**: Equity curve, P&L metrics, win rate, drawdown
- **Live Trading**: Monitor positions, kill switch, system status
- **Trade History**: View all closed trades with filters

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts (for data visualization)
- React Hooks for state management

## API Integration

The UI connects to the Aurora Trader API at `NEXT_PUBLIC_API_URL`:

- `GET /health` - Health check
- `GET /api/status` - System status
- `GET /api/metrics` - Trading metrics
- `GET /api/metrics/positions` - Current positions
- `GET /api/metrics/trades` - Trade history
- `GET /api/metrics/equity` - Equity curve
- `POST /api/halt` - Emergency kill switch
- `POST /api/resume` - Resume trading
