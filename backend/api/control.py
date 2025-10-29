"""
Control endpoints for managing trading operations.
"""

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.engine.risk.limits import RiskLimits, RiskLimitsConfig
from backend.engine.utils.config import get_settings

router = APIRouter()
settings = get_settings()

# Global risk limits instance (shared across requests)
risk_limits = RiskLimits(
    RiskLimitsConfig(
        max_daily_loss=settings.max_daily_loss,
        max_portfolio_exposure=settings.max_portfolio_exposure,
        symbol_whitelist=settings.symbols,
    )
)


class HaltRequest(BaseModel):
    """Request to activate kill switch."""

    reason: str


class HaltResponse(BaseModel):
    """Kill switch response."""

    kill_switch_active: bool
    message: str


class StatusResponse(BaseModel):
    """System status response."""

    worker_enabled: bool
    kill_switch_active: bool
    trading_enabled: bool
    daily_pnl: float
    daily_pnl_pct: float
    max_daily_loss_pct: float
    symbol_whitelist: list


@router.post("/halt", response_model=HaltResponse)
async def halt_trading(request: HaltRequest) -> Dict:
    """
    Emergency kill switch - halt all trading.

    Args:
        request: Halt request with reason

    Returns:
        Kill switch status
    """
    risk_limits.activate_kill_switch(request.reason)

    return {
        "kill_switch_active": True,
        "message": f"Kill switch activated: {request.reason}",
    }


@router.post("/resume", response_model=HaltResponse)
async def resume_trading() -> Dict:
    """
    Deactivate kill switch and resume trading.

    Returns:
        Kill switch status
    """
    risk_limits.deactivate_kill_switch()

    return {
        "kill_switch_active": False,
        "message": "Kill switch deactivated - trading resumed",
    }


@router.get("/status", response_model=StatusResponse)
async def get_status() -> Dict:
    """
    Get current system status.

    Returns:
        System status including kill switch, daily P&L, etc.
    """
    status = risk_limits.get_status()

    return {
        "worker_enabled": settings.worker_enabled,
        "kill_switch_active": status["kill_switch_active"],
        "trading_enabled": status["trading_enabled"],
        "daily_pnl": status["daily_pnl"],
        "daily_pnl_pct": status["daily_pnl_pct"],
        "max_daily_loss_pct": status["max_daily_loss_pct"],
        "symbol_whitelist": status["symbol_whitelist"],
    }
