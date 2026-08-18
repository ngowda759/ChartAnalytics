"""AI Trade Review Service - Analyzes trades and provides educational insights."""
from typing import List, Dict, Any, Optional
from enum import Enum
import structlog

logger = structlog.get_logger()


class ReviewCategory(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    RISK = "risk"
    PSYCHOLOGY = "psychology"
    STRATEGY = "strategy"


class ReviewSeverity(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    IMPROVEMENT = "improvement"
    CRITICAL = "critical"


class TradeReview:
    """Analysis of a single trade."""

    def __init__(
        self,
        trade_id: str,
        category: ReviewCategory,
        severity: ReviewSeverity,
        title: str,
        description: str,
        recommendation: str,
        score_impact: float = 0,
    ):
        self.trade_id = trade_id
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.recommendation = recommendation
        self.score_impact = score_impact

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "score_impact": self.score_impact,
        }


class TradeReviewReport:
    """Complete review report for a trade."""

    def __init__(
        self,
        trade_id: str,
        overall_score: float,
        entry_score: float,
        exit_score: float,
        risk_score: float,
        psychology_score: float,
        reviews: List[TradeReview],
        summary: str,
        key_improvements: List[str],
    ):
        self.trade_id = trade_id
        self.overall_score = overall_score
        self.entry_score = entry_score
        self.exit_score = exit_score
        self.risk_score = risk_score
        self.psychology_score = psychology_score
        self.reviews = reviews
        self.summary = summary
        self.key_improvements = key_improvements

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "overall_score": round(self.overall_score, 2),
            "scores": {
                "entry": round(self.entry_score, 2),
                "exit": round(self.exit_score, 2),
                "risk": round(self.risk_score, 2),
                "psychology": round(self.psychology_score, 2),
            },
            "reviews": [r.to_dict() for r in self.reviews],
            "summary": self.summary,
            "key_improvements": self.key_improvements,
        }


class TradeReviewService:
    """Service for analyzing and reviewing trades."""

    def analyze_trade(
        self,
        trade_id: str,
        entry_price: float,
        exit_price: Optional[float],
        stop_loss: float,
        target: float,
        quantity: int,
        trade_type: str,
        strategy: str,
        pnl: Optional[float] = None,
        holding_period_minutes: Optional[int] = None,
    ) -> TradeReviewReport:
        """Analyze a trade and provide educational feedback."""
        logger.info("analyzing_trade", trade_id=trade_id)

        reviews: List[TradeReview] = []
        entry_score = 50.0
        exit_score = 50.0
        risk_score = 50.0
        psychology_score = 50.0

        # Entry Analysis
        entry_reviews, entry_score = self._analyze_entry(
            trade_id, entry_price, stop_loss, target, strategy
        )
        reviews.extend(entry_reviews)

        # Exit Analysis (if trade is closed)
        if exit_price is not None:
            exit_reviews, exit_score = self._analyze_exit(
                trade_id, entry_price, exit_price, stop_loss, target, trade_type, pnl
            )
            reviews.extend(exit_reviews)

        # Risk Analysis
        risk_reviews, risk_score = self._analyze_risk(
            trade_id, entry_price, stop_loss, target, quantity, pnl
        )
        reviews.extend(risk_reviews)

        # Psychology Analysis
        psych_reviews, psychology_score = self._analyze_psychology(
            trade_id, exit_price, pnl, holding_period_minutes
        )
        reviews.extend(psych_reviews)

        # Calculate overall score
        overall_score = (
            entry_score * 0.25 + exit_score * 0.25 +
            risk_score * 0.25 + psychology_score * 0.25
        )

        # Generate summary and key improvements
        summary = self._generate_summary(trade_id, overall_score, pnl)
        key_improvements = self._get_key_improvements(reviews)

        return TradeReviewReport(
            trade_id=trade_id,
            overall_score=overall_score,
            entry_score=entry_score,
            exit_score=exit_score,
            risk_score=risk_score,
            psychology_score=psychology_score,
            reviews=reviews,
            summary=summary,
            key_improvements=key_improvements,
        )

    def _analyze_entry(
        self,
        trade_id: str,
        entry_price: float,
        stop_loss: float,
        target: float,
        strategy: str,
    ) -> tuple[List[TradeReview], float]:
        """Analyze trade entry quality."""
        reviews = []
        score = 50.0

        rr_ratio = abs(target - entry_price) / abs(entry_price - stop_loss)

        # Check risk-reward ratio
        if rr_ratio >= 2:
            reviews.append(TradeReview(
                trade_id=trade_id,
                category=ReviewCategory.ENTRY,
                severity=ReviewSeverity.POSITIVE,
                title="Good Risk-Reward Ratio",
                description=f"Your trade has a risk-reward ratio of {rr_ratio:.2f}:1, which is excellent for long-term profitability.",
                recommendation="Maintain this practice of only taking trades with favorable RR ratios.",
                score_impact=10.0,
            ))
            score += 10
        elif rr_ratio >= 1.5:
            reviews.append(TradeReview(
                trade_id=trade_id,
                category=ReviewCategory.ENTRY,
                severity=ReviewSeverity.NEUTRAL,
                title="Acceptable Risk-Reward",
                description=f"RR ratio of {rr_ratio:.2f}:1 is acceptable. Consider waiting for better setups.",
                recommendation="Aim for at least 2:1 RR ratio for consistent profitability.",
                score_impact=0.0,
            ))
        elif rr_ratio < 1:
            reviews.append(TradeReview(
                trade_id=trade_id,
                category=ReviewCategory.ENTRY,
                severity=ReviewSeverity.IMPROVEMENT,
                title="Poor Risk-Reward Ratio",
                description=f"RR ratio of {rr_ratio:.2f}:1 makes it difficult to be profitable over time.",
                recommendation="Only enter trades with at least 1.5:1 RR, ideally 2:1 or higher.",
                score_impact=-10.0,
            ))
            score -= 10

        # Check entry proximity to key levels
        reviews.append(TradeReview(
            trade_id=trade_id,
            category=ReviewCategory.ENTRY,
            severity=ReviewSeverity.NEUTRAL,
            title="Entry Strategy Review",
            description=f"Entry analysis for {strategy} strategy.",
            recommendation="Ensure entries are made at key support/resistance or indicator signals.",
            score_impact=0.0,
        ))

        return reviews, max(0, min(100, score))

    def _analyze_exit(
        self,
        trade_id: str,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        target: float,
        trade_type: str,
        pnl: Optional[float],
    ) -> tuple[List[TradeReview], float]:
        """Analyze trade exit quality."""
        reviews = []
        score = 50.0

        is_long = trade_type.lower() == "long"
        max_potential = abs(target - entry_price)
        actual_movement = abs(exit_price - entry_price)
        exit_efficiency = (actual_movement / max_potential * 100) if max_potential > 0 else 0

        if pnl is not None:
            if pnl > 0:
                # Profitable trade analysis
                if exit_efficiency >= 80:
                    reviews.append(TradeReview(
                        trade_id=trade_id,
                        category=ReviewCategory.EXIT,
                        severity=ReviewSeverity.POSITIVE,
                        title="Excellent Exit Timing",
                        description=f"You captured {exit_efficiency:.1f}% of the potential move - excellent discipline!",
                        recommendation="Continue this practice of letting winners run.",
                        score_impact=15.0,
                    ))
                    score += 15
                elif exit_efficiency >= 50:
                    reviews.append(TradeReview(
                        trade_id=trade_id,
                        category=ReviewCategory.EXIT,
                        severity=ReviewSeverity.NEUTRAL,
                        title="Room for Exit Improvement",
                        description=f"You captured {exit_efficiency:.1f}% of the potential move.",
                        recommendation="Consider using trailing stops to capture more of winning moves.",
                        score_impact=0.0,
                    ))
                else:
                    reviews.append(TradeReview(
                        trade_id=trade_id,
                        category=ReviewCategory.EXIT,
                        severity=ReviewSeverity.IMPROVEMENT,
                        title="Early Exit",
                        description=f"You exited early, capturing only {exit_efficiency:.1f}% of the move.",
                        recommendation="Practice letting winners breathe - use trailing stops instead of fixed targets.",
                        score_impact=-10.0,
                    ))
                    score -= 10
            else:
                # Losing trade analysis
                if abs(exit_price - stop_loss) / abs(entry_price - stop_loss) < 0.2:
                    reviews.append(TradeReview(
                        trade_id=trade_id,
                        category=ReviewCategory.EXIT,
                        severity=ReviewSeverity.POSITIVE,
                        title="Quick Loss Cut",
                        description="You exited quickly when the trade didn't work - good discipline!",
                        recommendation="This is the correct approach. Small losses preserve capital.",
                        score_impact=10.0,
                    ))
                    score += 10
                else:
                    reviews.append(TradeReview(
                        trade_id=trade_id,
                        category=ReviewCategory.EXIT,
                        severity=ReviewSeverity.IMPROVEMENT,
                        title="Extended Loss",
                        description="You held the losing position too long.",
                        recommendation="Stick to your stop loss strictly. Don't average into losers.",
                        score_impact=-15.0,
                    ))
                    score -= 15

        return reviews, max(0, min(100, score))

    def _analyze_risk(
        self,
        trade_id: str,
        entry_price: float,
        stop_loss: float,
        target: float,
        quantity: int,
        pnl: Optional[float],
    ) -> tuple[List[TradeReview], float]:
        """Analyze risk management."""
        reviews = []
        score = 50.0

        risk_amount = abs(entry_price - stop_loss) * quantity
        capital_risk_percent = (risk_amount / 100000) * 100  # Assuming 1 lakh capital

        if capital_risk_percent <= 1:
            reviews.append(TradeReview(
                trade_id=trade_id,
                category=ReviewCategory.RISK,
                severity=ReviewSeverity.POSITIVE,
                title="Excellent Position Sizing",
                description=f"Risk of ₹{risk_amount:.0f} ({capital_risk_percent:.1f}% of capital) is within guidelines.",
                recommendation="Maintaining 1-2% risk per trade is key to long-term survival.",
                score_impact=15.0,
            ))
            score += 15
        elif capital_risk_percent <= 2:
            reviews.append(TradeReview(
                trade_id=trade_id,
                category=ReviewCategory.RISK,
                severity=ReviewSeverity.NEUTRAL,
                title="Acceptable Risk Level",
                description=f"Risk of {capital_risk_percent:.1f}% is acceptable but consider reducing.",
                recommendation="Aim for 1% or less risk per trade for optimal risk management.",
                score_impact=0.0,
            ))
        else:
            reviews.append(TradeReview(
                trade_id=trade_id,
                category=ReviewCategory.RISK,
                severity=ReviewSeverity.CRITICAL,
                title="Over-Risked Trade",
                description=f"Risk of {capital_risk_percent:.1f}% per trade is dangerously high!",
                recommendation="Never risk more than 2% per trade. Large losses require even larger gains to recover.",
                score_impact=-20.0,
            ))
            score -= 20

        return reviews, max(0, min(100, score))

    def _analyze_psychology(
        self,
        trade_id: str,
        exit_price: Optional[float],
        pnl: Optional[float],
        holding_period: Optional[int],
    ) -> tuple[List[TradeReview], float]:
        """Analyze trading psychology."""
        reviews = []
        score = 50.0

        if pnl is not None:
            if pnl > 0:
                # Positive trade - check for revenge trading indicators
                reviews.append(TradeReview(
                    trade_id=trade_id,
                    category=ReviewCategory.PSYCHOLOGY,
                    severity=ReviewSeverity.NEUTRAL,
                    title="Emotional State Review",
                    description="Winning trade - focus on not becoming overconfident.",
                    recommendation="Stay disciplined after wins. Avoid increasing position sizes.",
                    score_impact=5.0,
                ))
                score += 5
            else:
                # Losing trade - check for proper emotional handling
                reviews.append(TradeReview(
                    trade_id=trade_id,
                    category=ReviewCategory.PSYCHOLOGY,
                    severity=ReviewSeverity.NEUTRAL,
                    title="Post-Loss Analysis",
                    description="Losses are part of trading. Focus on process over outcomes.",
                    recommendation="Never revenge trade. Take a break after losses and review objectively.",
                    score_impact=0.0,
                ))

        return reviews, max(0, min(100, score))

    def _generate_summary(self, trade_id: str, score: float, pnl: Optional[float]) -> str:
        """Generate a summary of the trade review."""
        if score >= 80:
            quality = "excellent"
            desc = "This was a well-executed trade with good entry, risk management, and exit."
        elif score >= 60:
            quality = "good"
            desc = "This trade was well-planned with minor areas for improvement."
        elif score >= 40:
            quality = "average"
            desc = "This trade had mixed results. Review the recommendations for improvement."
        else:
            quality = "poor"
            desc = "This trade needs significant improvement. Focus on the key areas identified."

        pnl_desc = f"P&L: ₹{pnl:.2f}" if pnl is not None else ""
        return f"Trade #{trade_id} rated as {quality}. {desc} {pnl_desc}"

    def _get_key_improvements(self, reviews: List[TradeReview]) -> List[str]:
        """Extract key improvement areas from reviews."""
        improvements = [
            r.recommendation
            for r in reviews
            if r.severity in (ReviewSeverity.IMPROVEMENT, ReviewSeverity.CRITICAL)
        ]
        return improvements[:5]  # Return top 5 improvements


# Singleton instance
trade_review_service = TradeReviewService()
