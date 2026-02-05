"""World engine tests: determinism, rules, actions"""
import pytest
from engine.world import WorldEngine, Region, Resource, Agent
from engine.rules import RulesEngine

class TestWorldEngine:
    """World engine core tests"""
    
    def test_initial_state(self):
        """Test initial state"""
        engine = WorldEngine()
        assert engine.state.tick == 0
        assert engine.state.tax_rate == 0.05
        assert len(engine.agents) == 0
        assert engine.state.state_hash != ""
    
    def test_register_agent(self):
        """Test agent registration"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        
        assert agent.wallet == "0xTest"
        assert agent.name == "TestBot"
        assert agent.region == Region.DOCK
        assert agent.energy == 100
        assert agent.credits == 1000
        assert len(engine.agents) == 1
    
    def test_register_duplicate(self):
        """Test duplicate registration returns existing agent"""
        engine = WorldEngine()
        agent1 = engine.register_agent("0xTest", "TestBot")
        agent2 = engine.register_agent("0xTest", "TestBot2")
        
        assert agent1 is agent2
        assert len(engine.agents) == 1
    
    def test_process_tick(self):
        """Test tick processing"""
        engine = WorldEngine()
        engine.register_agent("0xTest", "TestBot")
        
        # Consume some AP
        engine.agents["0xTest"].energy = 50
        
        result = engine.process_tick()
        
        assert result["tick"] == 1
        assert engine.state.tick == 1
        assert engine.agents["0xTest"].energy == 55  # +5 AP recovery

class TestDeterminism:
    """Determinism tests"""
    
    def test_same_input_same_output(self):
        """Same input produces same output"""
        # Run 1
        engine1 = WorldEngine()
        agent1 = engine1.register_agent("0xTest", "TestBot")
        rules1 = RulesEngine(engine1)
        
        rules1.execute_action(agent1, "move", {"target": "mine"})
        rules1.execute_action(agent1, "harvest", {})
        engine1.process_tick()
        
        hash1 = engine1.state.state_hash
        inv1 = dict(agent1.inventory)
        
        # Run 2 (exact same operations)
        engine2 = WorldEngine()
        agent2 = engine2.register_agent("0xTest", "TestBot")
        rules2 = RulesEngine(engine2)
        
        rules2.execute_action(agent2, "move", {"target": "mine"})
        rules2.execute_action(agent2, "harvest", {})
        engine2.process_tick()
        
        hash2 = engine2.state.state_hash
        inv2 = dict(agent2.inventory)
        
        assert hash1 == hash2
        assert inv1 == inv2
    
    def test_ledger_consistency(self):
        """Verify ledger record consistency"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        rules = RulesEngine(engine)
        
        rules.execute_action(agent, "move", {"target": "mine"})
        rules.execute_action(agent, "harvest", {})
        
        # Should have 3 ledger entries (register + move + harvest)
        assert len(engine.ledger) == 3
        assert engine.ledger[0]["action"] == "register"
        assert engine.ledger[1]["action"] == "move"
        assert engine.ledger[2]["action"] == "harvest"

class TestRulesEngine:
    """Rules engine tests"""
    
    def test_move(self):
        """Test move action"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "move", {"target": "mine"})
        
        assert result["success"] == True
        assert agent.region == Region.MINE
        assert agent.energy == 95  # 100 - 5
    
    def test_move_insufficient_ap(self):
        """Test insufficient AP cannot move"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.energy = 3
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "move", {"target": "mine"})
        
        assert result["success"] == False
        assert agent.region == Region.DOCK
    
    def test_harvest_in_mine(self):
        """Test harvesting in mine"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.region = Region.MINE
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "harvest", {})
        
        assert result["success"] == True
        assert agent.energy == 80  # 100 - 20
        assert sum(agent.inventory.values()) > 0
    
    def test_harvest_invalid_region(self):
        """Test cannot harvest in non-harvest region"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.region = Region.MARKET
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "harvest", {})
        
        assert result["success"] == False
    
    def test_rest(self):
        """Test rest action"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.energy = 50
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "rest", {})
        
        assert result["success"] == True
        assert agent.energy == 70  # 50 + 20
    
    def test_rest_in_tavern(self):
        """Test resting in tavern recovers more"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.energy = 50
        agent.region = Region.TAVERN
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "rest", {})
        
        assert result["success"] == True
        assert agent.energy == 80  # 50 + 30
    
    def test_sell_in_market(self):
        """Test selling in market"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.region = Region.MARKET
        agent.inventory["iron"] = 10
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "place_order", {
            "resource": "iron", "side": "sell", "quantity": 5
        })
        
        assert result["success"] == True
        assert agent.inventory["iron"] == 5
        # 5 * 10 * 0.95 = 47.5 -> 47
        assert agent.credits == 1000 + 47
    
    def test_buy_in_market(self):
        """Test buying in market"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.region = Region.MARKET
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "place_order", {
            "resource": "iron", "side": "buy", "quantity": 5
        })
        
        assert result["success"] == True
        assert agent.inventory.get("iron", 0) == 5
        assert agent.credits == 1000 - 50  # 5 * 10
    
    def test_sell_not_in_market(self):
        """Test cannot trade outside market"""
        engine = WorldEngine()
        agent = engine.register_agent("0xTest", "TestBot")
        agent.inventory["iron"] = 10
        rules = RulesEngine(engine)
        
        result = rules.execute_action(agent, "place_order", {
            "resource": "iron", "side": "sell", "quantity": 5
        })
        
        assert result["success"] == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
