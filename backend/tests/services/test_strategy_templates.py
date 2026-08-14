"""Tests for the strategy-templates engine (ported from daily_stock_analysis)."""
import pytest

from app.services import strategy_templates as st


class TestStrategyTemplates:
    def test_templates_ship_and_load(self):
        slugs = st.list_template_slugs()
        assert slugs, "expected bundled strategy template YAMLs"
        for slug in slugs:
            tpl = st.load_template(slug)
            assert tpl is not None
            assert "name" in tpl and "rules" in tpl

    def test_load_unknown_slug_returns_none(self):
        assert st.load_template("does-not-exist") is None

    def test_evaluate_all_returns_scored_signals(self):
        rows = st.evaluate_all(limit_per_template=10)
        assert rows, "evaluate_all should never be empty"
        assert all(0 <= r.score <= 100 for r in rows)
        assert rows == sorted(rows, key=lambda r: r.score, reverse=True)

    def test_actions_partition_by_score(self):
        for row in st.evaluate_all(limit_per_template=25):
            if row.score >= 70:
                assert row.action == st.ACTION_BUY
            elif row.score >= 45:
                assert row.action == st.ACTION_HOLD
            else:
                assert row.action == st.ACTION_AVOID

    def test_buy_signals_carry_levels(self):
        rows = st.evaluate_all(limit_per_template=25)
        buys = [r for r in rows if r.action == st.ACTION_BUY]
        if not buys:
            pytest.skip("no buy signals in current universe hour")
        for r in buys:
            assert r.entry is not None and r.entry > 0
            assert r.stop_loss is not None and r.stop_loss < r.entry
            assert r.target is not None and r.target > r.entry

    def test_evaluate_symbol_deterministic_within_hour(self):
        tpl = st.load_template("bull_trend")
        a = st.evaluate_symbol("RELIANCE", "Reliance", 2967.0, tpl)
        b = st.evaluate_symbol("RELIANCE", "Reliance", 2967.0, tpl)
        assert a.score == b.score
        assert a.action == b.action

    def test_strategy_filter_scopes_to_template(self):
        tpl = st.load_template("ma_golden_cross")
        rows = st.evaluate_template_universe(tpl, limit=30)
        assert rows
        assert all(r.strategy == "ma_golden_cross" for r in rows)

    def test_reasons_populated_when_rules_match(self):
        rows = [r for r in st.evaluate_all(limit_per_template=25) if r.reasons]
        assert rows, "at least some signals should carry matched-rule reasons"
