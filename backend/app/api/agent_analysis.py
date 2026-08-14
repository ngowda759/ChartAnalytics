"""TradingAgents-style multi-agent analysis API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

import structlog

from app.schemas.agent_analysis import (
    AgentAnalysisListResponse,
    AgentAnalysisResult,
    PortfolioRating,
)
from app.services.trading_agents import analyze_symbol, analyze_universe

logger = structlog.get_logger()
router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=AgentAnalysisResult,
    summary="Run the multi-agent analysis pipeline for a symbol",
)
async def get_agent_analysis(symbol: str, base: Optional[float] = Query(None)) -> AgentAnalysisResult:
    result = analyze_symbol(symbol, base=base)
    logger.info(
        "agent_analysis_completed",
        symbol=symbol,
        rating=result.final_decision.rating.value,
    )
    return result


@router.get(
    "/",
    response_model=AgentAnalysisListResponse,
    summary="Run the pipeline across the watchlist universe",
)
async def list_agent_analysis(
    limit: int = Query(25, ge=1, le=100),
) -> AgentAnalysisListResponse:
    results = analyze_universe(limit=limit)

    def bucket(r: AgentAnalysisResult) -> str:
        rating = r.final_decision.rating
        if rating in (PortfolioRating.BUY, PortfolioRating.OVERWEIGHT):
            return "buy"
        if rating in (PortfolioRating.SELL, PortfolioRating.UNDERWEIGHT):
            return "sell"
        return "hold"

    buy = sum(1 for r in results if bucket(r) == "buy")
    sell = sum(1 for r in results if bucket(r) == "sell")
    hold = sum(1 for r in results if bucket(r) == "hold")
    return AgentAnalysisListResponse(
        total=len(results),
        buy_count=buy,
        sell_count=sell,
        hold_count=hold,
        results=results,
    )
