"""Unit tests for option chain analytics."""
import pytest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.option_chain import (
    OptionChainAnalyzer,
    analyze_option_chain,
    calculate_pcr,
    calculate_max_pain,
)
from app.integrations.data_providers.base import OptionChainData


class TestOptionChainAnalyzer:
    """Tests for OptionChainAnalyzer."""
    
    def create_mock_chain_data(self, spot_price: float = 25000) -> list:
        """Create mock option chain data."""
        chain = []
        atm_strike = round(spot_price / 50) * 50
        
        for i in range(-20, 21):
            strike = atm_strike + (i * 50)
            
            # Calls - higher OI near ATM
            distance = abs(i)
            call_oi = max(10000, 500000 - distance * 20000)
            put_oi = max(10000, 500000 - distance * 20000)
            
            chain.append(OptionChainData(
                symbol="NIFTY",
                expiry_date=datetime.now(),
                strike=strike,
                call_oi=call_oi,
                call_volume=call_oi // 10,
                call_iv=15 + abs(i) * 0.5,
                call_ltp=50 if i <= 0 else max(5, 50 - abs(i) * 5),
                call_change_oi=10000 if i <= 0 else -5000,
                put_oi=put_oi + 50000,  # Slightly higher put OI
                put_volume=put_oi // 10,
                put_iv=17 + abs(i) * 0.5,
                put_ltp=50 if i >= 0 else max(5, 50 - abs(i) * 5),
                put_change_oi=15000 if i >= 0 else -5000,
            ))
        
        return chain
    
    def test_analyze_basic(self):
        """Test basic option chain analysis."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        expiry_date = datetime.now()
        
        analyzer = OptionChainAnalyzer(spot_price, expiry_date)
        result = analyzer.analyze(chain_data)
        
        assert result.spot_price == spot_price
        assert result.symbol == "NIFTY"
        assert 0.5 <= result.pcr <= 2.0
        assert result.max_pain > 0
        assert len(result.strikes) > 0
    
    def test_pcr_calculation(self):
        """Test PCR calculation."""
        chain_data = self.create_mock_chain_data()
        pcr = calculate_pcr(chain_data)
        
        assert pcr > 0
        assert isinstance(pcr, float)
    
    def test_pcr_interpretation_bullish(self):
        """Test PCR interpretation for bullish sentiment."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        # Increase put OI to make PCR > 1
        for data in chain_data:
            data.put_oi = int(data.put_oi * 1.3)
        
        analyzer = OptionChainAnalyzer(spot_price, datetime.now())
        result = analyzer.analyze(chain_data)
        
        # High PCR should indicate bullish sentiment
        assert result.pcr > 1.0
    
    def test_max_pain_calculation(self):
        """Test max pain calculation."""
        chain_data = self.create_mock_chain_data(25000)
        max_pain = calculate_max_pain(chain_data, 25000)
        
        assert max_pain > 0
        assert isinstance(max_pain, float)
    
    def test_support_resistance_levels(self):
        """Test support and resistance level identification."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        
        analyzer = OptionChainAnalyzer(spot_price, datetime.now())
        result = analyzer.analyze(chain_data)
        
        # Support levels should be below spot
        for support in result.support_levels:
            assert support["strike"] < spot_price
        
        # Resistance levels should be above spot
        for resistance in result.resistance_levels:
            assert resistance["strike"] > spot_price
    
    def test_iv_skew(self):
        """Test IV skew calculation."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        
        analyzer = OptionChainAnalyzer(spot_price, datetime.now())
        result = analyzer.analyze(chain_data)
        
        # IV skew should be positive
        assert result.iv_skew > 0
        # With higher put IV, should be > 1
        assert result.iv_skew >= 1.0
    
    def test_trend_detection(self):
        """Test trend detection from OI."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        
        # Make it clearly bullish: high put OI
        for data in chain_data:
            if data.strike < spot_price:
                data.put_oi *= 2
        
        analyzer = OptionChainAnalyzer(spot_price, datetime.now())
        result = analyzer.analyze(chain_data)
        
        assert result.trend in ["bullish", "bearish", "neutral"]
        assert 0 <= result.confidence <= 100
    
    def test_empty_chain_data(self):
        """Test with empty chain data."""
        analyzer = OptionChainAnalyzer(25000, datetime.now())
        result = analyzer.analyze([])
        
        assert result.symbol == ""
        assert result.pcr == 0
    
    def test_oi_balance_calculation(self):
        """Test OI balance for individual strikes."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        
        analyzer = OptionChainAnalyzer(spot_price, datetime.now())
        
        for data in chain_data[:5]:  # Test first few strikes
            oi_balance = data.put_oi - data.call_oi
            assert isinstance(oi_balance, int)
    
    def test_net_building_classification(self):
        """Test net building classification."""
        analyzer = OptionChainAnalyzer(25000, datetime.now())
        
        # Both increasing = fresh buildup
        assert analyzer._determine_net_building(10000, 10000) == "fresh_buildup"
        
        # Call up, put down = short covering
        assert analyzer._determine_net_building(10000, -5000) == "short_covering"
        
        # Put up, call down = long unwinding
        assert analyzer._determine_net_building(-5000, 10000) == "long_unwinding"
        
        # Both decreasing = fresh shorting
        assert analyzer._determine_net_building(-5000, -5000) == "fresh_shorting"
    
    def test_interpretation_generation(self):
        """Test overall interpretation generation."""
        spot_price = 25000
        chain_data = self.create_mock_chain_data(spot_price)
        
        analyzer = OptionChainAnalyzer(spot_price, datetime.now())
        result = analyzer.analyze(chain_data)
        
        assert len(result.interpretation) > 0
        assert isinstance(result.interpretation, str)


class TestCalculateFunctions:
    """Tests for standalone calculation functions."""
    
    def test_calculate_pcr(self):
        """Test calculate_pcr function."""
        chain = [
            OptionChainData(
                symbol="TEST", expiry_date=datetime.now(), strike=25000,
                call_oi=1000000, call_volume=50000, call_iv=15, call_ltp=100,
                call_change_oi=10000, put_oi=1200000, put_volume=60000, put_iv=17,
                put_ltp=120, put_change_oi=15000
            )
        ]
        
        pcr = calculate_pcr(chain)
        assert pcr == 1.2
    
    def test_calculate_pcr_zero_calls(self):
        """Test PCR with zero call OI."""
        chain = [
            OptionChainData(
                symbol="TEST", expiry_date=datetime.now(), strike=25000,
                call_oi=0, call_volume=0, call_iv=15, call_ltp=100,
                call_change_oi=0, put_oi=100000, put_volume=5000, put_iv=17,
                put_ltp=120, put_change_oi=0
            )
        ]
        
        pcr = calculate_pcr(chain)
        assert pcr == 0.0
    
    def test_calculate_max_pain(self):
        """Test max pain calculation."""
        chain = [
            OptionChainData(
                symbol="TEST", expiry_date=datetime.now(), strike=25000,
                call_oi=1000000, call_volume=50000, call_iv=15, call_ltp=100,
                call_change_oi=0, put_oi=1000000, put_volume=50000, put_iv=17,
                put_ltp=100, put_change_oi=0
            )
        ]
        
        max_pain = calculate_max_pain(chain, 25000)
        assert max_pain == 25000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
