"""
Test suite for Pokemon Card Agent.
Run with: python -m pytest tests/ -v
"""
import pytest
import sqlite3
import tempfile
import os
from datetime import datetime

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grading.estimator import estimate_grade, assess_condition, get_grading_cost_estimate
from search.cards import _normalize, _similarity
from alerts.tracker import init_alerts_table, create_alert, get_user_alerts, delete_alert, check_alerts
from collection.manager import init_collection_tables, add_to_collection, get_collection, get_portfolio_summary


# ===== Fixtures =====

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Override DB_PATH for testing
    import db.connection
    original_path = db.connection.DB_PATH
    db.connection.DB_PATH = path
    
    # Initialize schema
    from db.connection import init_db
    init_db()
    
    yield path
    
    # Cleanup
    db.connection.DB_PATH = original_path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_cards(temp_db):
    """Insert sample cards into test database."""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    
    # Insert test set
    conn.execute(
        "INSERT INTO sets (id, name, series, release_date, logo_url, total, value_index) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("test-sv", "Test Set", "Scarlet & Violet", "2024-01", "", 100, 5000)
    )
    
    # Insert test cards
    cards = [
        ("test-1", "test-sv", "Charizard EX", "Ultra Rare", "Pokémon", "", 150.00, 120.00, 180.00),
        ("test-2", "test-sv", "Pikachu", "Common", "Pokémon", "", 5.00, 3.00, 8.00),
        ("test-3", "test-sv", "Mewtwo", "Rare Holo", "Pokémon", "", 45.00, 35.00, 55.00),
    ]
    
    for card in cards:
        conn.execute(
            """INSERT INTO cards (id, set_id, name, rarity, supertype, subtype, tcgplayer_market, tcgplayer_low, tcgplayer_high)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            card
        )
    
    conn.commit()
    conn.close()
    
    return ["test-1", "test-2", "test-3"]


# ===== Grading Tests =====

class TestGradingEstimator:
    """Test the grading estimator module."""
    
    def test_estimate_grade_empty(self):
        """Test grade estimation with empty input."""
        result = estimate_grade("")
        assert "Unable" in result or "no condition" in result.lower()
    
    def test_estimate_grade_gem_mint(self):
        """Test grade estimation for pristine condition."""
        result = estimate_grade("gem mint, pack fresh, flawless")
        assert "10" in result or "Gem Mint" in result
    
    def test_estimate_grade_with_damage(self):
        """Test grade estimation for damaged card."""
        result = estimate_grade("heavy crease, water damage, edge wear")
        assert any(x in result for x in ["1", "2", "3", "Poor", "Fair"])
    
    def test_assess_condition_detailed(self):
        """Test detailed condition assessment."""
        result = assess_condition("light edge wear, NM")
        assert "grade" in result
        assert "confidence" in result
        assert "recommendation" in result
    
    def test_grading_cost_estimate(self):
        """Test grading cost estimation."""
        result = get_grading_cost_estimate(100.0, 9)
        assert "grading_costs" in result
        assert "psa" in result["grading_costs"]
        assert "potential_net_gain" in result


# ===== Search Tests =====

class TestSearch:
    """Test the search module."""
    
    def test_normalize(self):
        """Test text normalization."""
        assert _normalize("Charizard EX") == "charizardex"
        assert _normalize("Pikachu & Raichu") == "pikachuraichu"
    
    def test_similarity(self):
        """Test string similarity calculation."""
        # Exact match
        assert _similarity("charizard", "charizard") == 1.0
        # Close match
        assert _similarity("charizard", "charzard") > 0.8
        # Different
        assert _similarity("charizard", "pikachu") < 0.5


# ===== Alerts Tests =====

class TestAlerts:
    """Test the price alerts system."""
    
    def test_create_alert(self, temp_db, sample_cards):
        """Test creating a price alert."""
        alert = create_alert("user123", "test-1", "above", 200.0)
        assert alert is not None
        assert alert.card_id == "test-1"
        assert alert.threshold == 200.0
    
    def test_get_user_alerts(self, temp_db, sample_cards):
        """Test retrieving user alerts."""
        create_alert("user123", "test-1", "above", 200.0)
        create_alert("user123", "test-2", "below", 3.0)
        
        alerts = get_user_alerts("user123")
        assert len(alerts) == 2
    
    def test_delete_alert(self, temp_db, sample_cards):
        """Test deleting an alert."""
        alert = create_alert("user123", "test-1", "above", 200.0)
        result = delete_alert(alert.id, "user123")
        assert result is True
        
        # Verify deletion
        alerts = get_user_alerts("user123")
        assert len(alerts) == 0
    
    def test_check_alerts_triggered(self, temp_db, sample_cards):
        """Test alert checking when condition is met."""
        # Card test-1 has market price of 150
        create_alert("user123", "test-1", "above", 100.0)  # Should trigger
        
        triggered = check_alerts("user123")
        assert len(triggered) == 1
        assert triggered[0]["card_id"] == "test-1"
    
    def test_check_alerts_not_triggered(self, temp_db, sample_cards):
        """Test alert checking when condition is not met."""
        # Card test-1 has market price of 150
        create_alert("user123", "test-1", "above", 200.0)  # Should not trigger
        
        triggered = check_alerts("user123")
        assert len(triggered) == 0


# ===== Collection Tests =====

class TestCollection:
    """Test the collection/portfolio module."""
    
    def test_add_to_collection(self, temp_db, sample_cards):
        """Test adding card to collection."""
        result = add_to_collection("user123", "test-1", quantity=2, condition="NM", purchase_price=100.0)
        assert result is True
    
    def test_get_collection(self, temp_db, sample_cards):
        """Test retrieving collection."""
        add_to_collection("user123", "test-1", quantity=2, condition="NM")
        add_to_collection("user123", "test-2", quantity=1, condition="M")
        
        items = get_collection("user123")
        assert len(items) == 2
        
        # Check calculated fields
        for item in items:
            assert "current_value" in item
            assert "profit_loss" in item or item.get("purchase_price") is None
    
    def test_portfolio_summary(self, temp_db, sample_cards):
        """Test portfolio summary calculation."""
        add_to_collection("user123", "test-1", quantity=2, purchase_price=100.0)
        add_to_collection("user123", "test-2", quantity=1, purchase_price=5.0)
        
        summary = get_portfolio_summary("user123")
        assert "total_value" in summary
        assert "total_cost" in summary
        assert "profit_loss" in summary
        assert summary["total_cards"] == 3  # 2 + 1
        assert summary["unique_cards"] == 2
    
    def test_portfolio_with_profit(self, temp_db, sample_cards):
        """Test profit/loss calculation."""
        # test-1 has market price of 150, bought at 100
        add_to_collection("user123", "test-1", quantity=1, purchase_price=100.0)
        
        summary = get_portfolio_summary("user123")
        assert summary["total_value"] == 150.0
        assert summary["total_cost"] == 100.0
        assert summary["profit_loss"] == 50.0
        assert summary["roi_percent"] == 50.0


# ===== Integration Tests =====

class TestIntegration:
    """Integration tests for multiple components."""
    
    def test_full_workflow(self, temp_db, sample_cards):
        """Test a complete user workflow."""
        user_id = "testuser"
        
        # 1. Add cards to collection
        add_to_collection(user_id, "test-1", quantity=1, purchase_price=120.0, condition="NM")
        add_to_collection(user_id, "test-2", quantity=2, purchase_price=4.0, condition="M")
        
        # 2. Check portfolio
        summary = get_portfolio_summary(user_id)
        assert summary["total_cards"] == 3
        assert summary["total_value"] > 0
        
        # 3. Set up price alert
        alert = create_alert(user_id, "test-1", "above", 200.0)
        assert alert is not None
        
        # 4. Check alerts
        triggered = check_alerts(user_id)
        # test-1 has price 150, so shouldn't trigger at 200
        assert len(triggered) == 0
        
        # 5. Create alert that will trigger
        create_alert(user_id, "test-1", "above", 100.0)
        triggered = check_alerts(user_id)
        assert len(triggered) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
