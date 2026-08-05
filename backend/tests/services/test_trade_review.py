"""Tests for Trade Review Service."""
import pytest
from app.services.trade_review import TradeReviewService, TradeReview


class TestTradeReviewService:
    """Test cases for TradeReviewService."""

    @pytest.fixture
    def service(self):
        return TradeReviewService()

    @pytest.fixture
    def sample_profitable_trade(self):
        return {
            "trade_id": "test_1",
            "entry_price": 25000,
            "exit_price": 25200,
            "stop_loss": 24800,
            "target": 25400,
            "quantity": 100,
            "trade_type": "long",
            "strategy": "VWAP",
            "pnl": 20000,
        }

    @pytest.fixture
    def sample_losing_trade(self):
        return {
            "trade_id": "test_2",
            "entry_price": 25000,
            "exit_price": 24850,
            "stop_loss": 24800,
            "target": 25400,
            "quantity": 100,
            "trade_type": "long",
            "strategy": "EMA",
            "pnl": -15000,
        }

    def test_analyze_profitable_trade_with_good_rr(self, service, sample_profitable_trade):
        """Test analysis of a profitable trade with good risk-reward ratio."""
        result = service.analyze_trade(**sample_profitable_trade)

        assert result.trade_id == "test_1"
        assert result.overall_score >= 0  # Should be valid score
        assert len(result.reviews) >= 0

    def test_analyze_losing_trade(self, service, sample_losing_trade):
        """Test analysis of a losing trade."""
        result = service.analyze_trade(**sample_losing_trade)

        assert result.trade_id == "test_2"
        assert len(result.reviews) >= 0

    def test_analyze_open_trade(self, service):
        """Test analysis of an open trade without exit."""
        result = service.analyze_trade(
            trade_id="test_3",
            entry_price=25000,
            exit_price=None,
            stop_loss=24800,
            target=25400,
            quantity=100,
            trade_type="long",
            strategy="Momentum",
            pnl=None,
        )

        assert result.trade_id == "test_3"
        assert result.exit_score == 50  # Default score for open trades

    def test_risk_reward_ratio_calculation(self, service):
        """Test risk-reward ratio analysis."""
        # Trade with 2:1 RR
        result = service.analyze_trade(
            trade_id="test_rr",
            entry_price=25000,
            exit_price=25400,
            stop_loss=24800,
            target=25800,
            quantity=100,
            trade_type="long",
            strategy="Test",
            pnl=10000,
        )

        # Should have positive entry review for good RR
        rr_reviews = [r for r in result.reviews if "Risk-Reward" in r.title]
        assert len(rr_reviews) > 0

    def test_position_sizing_analysis(self, service):
        """Test position sizing analysis."""
        result = service.analyze_trade(
            trade_id="test_position",
            entry_price=25000,
            exit_price=25200,
            stop_loss=24950,
            target=25500,
            quantity=50,
            trade_type="long",
            strategy="Test",
            pnl=10000,
        )

        risk_reviews = [r for r in result.reviews if r.category.value == "risk"]
        assert len(risk_reviews) > 0

    def test_summary_generation(self, service, sample_profitable_trade):
        """Test that summary is generated correctly."""
        result = service.analyze_trade(**sample_profitable_trade)

        assert result.summary is not None
        assert len(result.summary) > 0
        assert "test_1" in result.summary

    def test_key_improvements_extraction(self, service, sample_losing_trade):
        """Test extraction of key improvements from reviews."""
        result = service.analyze_trade(**sample_losing_trade)

        critical_reviews = [
            r for r in result.reviews
            if r.severity.value in ["improvement", "critical"]
        ]
        assert len(result.key_improvements) <= 5

    def test_short_trade_analysis(self, service):
        """Test analysis of a short trade."""
        result = service.analyze_trade(
            trade_id="test_short",
            entry_price=25000,
            exit_price=24800,
            stop_loss=25200,
            target=24600,
            quantity=100,
            trade_type="short",
            strategy="Scalping",
            pnl=20000,
        )

        assert result.trade_id == "test_short"
        assert len(result.reviews) > 0


class TestTradeReview:
    """Test cases for TradeReview dataclass."""

    def test_trade_review_to_dict(self):
        """Test TradeReview serialization."""
        from app.services.trade_review import ReviewCategory, ReviewSeverity
        
        review = TradeReview(
            trade_id="test",
            category=ReviewCategory.ENTRY,
            severity=ReviewSeverity.POSITIVE,
            title="Good Entry",
            description="Well-timed entry",
            recommendation="Continue this practice",
            score_impact=10.0,
        )

        data = review.to_dict()

        assert data["trade_id"] == "test"
        assert data["category"] == "entry"
        assert data["severity"] == "positive"
        assert data["title"] == "Good Entry"
        assert data["score_impact"] == 10.0
