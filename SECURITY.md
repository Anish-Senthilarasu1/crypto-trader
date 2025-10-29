# Security Policy

## Overview

Aurora Trader is a paper trading system designed with security best practices. This document outlines security considerations, key management, and incident response procedures.

## API Key Management

### Storage
- **NEVER** commit API keys to version control
- Store keys in `.env` file (gitignored)
- Use environment variables in production
- Rotate keys regularly (recommended: quarterly)

### Access Control
- Limit API key permissions to paper trading only
- Use read-only keys where possible
- Enable IP whitelisting if supported by broker
- Monitor API usage for anomalies

### Coinbase Advanced Trade
```bash
# Always use sandbox mode for paper trading
COINBASE_SANDBOX=1

# Recommended permissions:
# - Read account info
# - Place orders (sandbox only)
# - View order history
```

### Alpaca
```bash
# Always use paper trading endpoint
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Recommended permissions:
# - Account read
# - Trading (paper account only)
```

## Kill Switch

### Emergency Halt
The system includes an emergency kill switch to immediately stop all trading activity.

**Activation**:
```bash
curl -X POST http://localhost:8000/halt \
  -H "Content-Type: application/json" \
  -d '{"reason": "Emergency stop"}'
```

**Effects**:
- Stops live worker from placing new orders
- Existing orders remain active (manual cancellation required)
- Requires system restart to resume trading

### Automatic Triggers
The system automatically halts when:
1. Daily loss exceeds `MAX_DAILY_LOSS` threshold (default: 2%)
2. Critical system errors occur
3. Database connection failures

## Risk Controls

### Position Sizing
- Maximum risk per trade: `RISK_PER_TRADE` (default: 0.5%)
- Portfolio exposure cap: `MAX_PORTFOLIO_EXPOSURE` (default: 40%)
- ATR-based stop losses

### Symbol Whitelist
Only trade symbols explicitly listed in `SYMBOL_WHITELIST`:
```bash
SYMBOL_WHITELIST=BTC-USD,ETH-USD
```

### Daily Loss Limits
```bash
MAX_DAILY_LOSS=0.02  # 2% daily drawdown limit
```

## Audit Logging

### Database Records
All trading activity is logged to SQLite:
- Orders (timestamp, symbol, side, quantity, price)
- Fills (execution details)
- Trades (P&L, fees)
- System events (starts, stops, errors)

### Log Files
Application logs include:
- API requests/responses
- Strategy signals
- Risk decisions
- Error traces

**Location**: `logs/aurora_trader.log`

**Retention**: Recommended 90 days minimum

## Network Security

### API Endpoints
- Use HTTPS in production
- Implement rate limiting
- Add authentication middleware for sensitive endpoints
- CORS restricted to UI domain

### Recommended Nginx Config
```nginx
server {
    listen 443 ssl;
    server_name api.yourtrader.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Database Security

### SQLite
- File permissions: `600` (owner read/write only)
- Regular backups to encrypted storage
- Consider encryption at rest for production

### Migration to Postgres
For production deployments:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/aurora_trader
```

Enable:
- SSL connections
- Role-based access control
- Connection pooling
- Automated backups

## Alerting

### Slack Notifications
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Alerts triggered for:
- Daily loss threshold exceeded
- Kill switch activation
- System errors
- Unusual trading activity

### Email Alerts
```bash
EMAIL_SMTP_SERVER=smtp.gmail.com:587
EMAIL_SMTP_USER=alerts@yourtrader.com
EMAIL_SMTP_PASS=app_specific_password
EMAIL_ALERT_TO=admin@yourtrader.com
```

## Incident Response

### Suspected Compromise

1. **Immediate Actions**:
   - Execute kill switch: `POST /halt`
   - Revoke broker API keys
   - Change all credentials
   - Take system offline

2. **Investigation**:
   - Review audit logs
   - Check for unauthorized orders
   - Analyze access logs
   - Document findings

3. **Recovery**:
   - Generate new API keys
   - Update `.env` file
   - Verify system integrity
   - Resume operations cautiously

### Unusual Activity

1. **Check metrics**: `GET /metrics`
2. **Review recent trades**: Check database
3. **Examine logs**: `logs/aurora_trader.log`
4. **Verify strategy parameters**: `GET /config`
5. **If suspicious**: Execute kill switch

## Best Practices

### Development
- Use separate API keys for dev/staging/prod
- Never log sensitive credentials
- Sanitize error messages (no key exposure)
- Keep dependencies updated

### Deployment
- Use secrets management (Vault, AWS Secrets Manager)
- Enable firewall rules
- Monitor resource usage
- Implement backup/restore procedures

### Monitoring
- Daily metrics review
- Weekly performance analysis
- Monthly security audit
- Quarterly key rotation

## Responsible Disclosure

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email: security@yourtrader.com (update with actual contact)
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and provide updates every 72 hours until resolution.

## Compliance

### Paper Trading Disclaimer
Aurora Trader is designed for **paper trading only**. It:
- Uses sandbox/paper trading APIs exclusively
- Does not execute real trades
- Is for educational and testing purposes

### Data Privacy
- No PII is collected or stored
- Trading data remains local (SQLite)
- No external analytics or tracking

## Updates

This security policy is reviewed quarterly and updated as needed.

**Last Updated**: 2025-10-29
**Version**: 0.1.0
