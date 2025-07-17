"""Tests for Insurance Agent V0.1"""
import pytest
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.insurance_agent import InsuranceAgent, run_insurance_agent
from agents.tools.insurance import collect_event_data, calculate_loss_ratio
from agents.core.planner import planner_node, extract_event_type
from agents.core.router import tool_router, determine_tools_from_plan
from agents.core.executor import executor_layer


class TestInsuranceTools:
    """Test insurance tools"""
    
    @pytest.mark.asyncio
    async def test_collect_event_data(self):
        """Test collect_event_data tool"""
        result = await collect_event_data.ainvoke({"event_type": "typhoon"})
        
        assert isinstance(result, dict)
        assert result["event_type"] == "typhoon"
        assert "historical_frequency" in result
        assert "data_source" in result
        assert 0 <= result["historical_frequency"] <= 1
    
    @pytest.mark.asyncio
    async def test_calculate_loss_ratio(self):
        """Test calculate_loss_ratio tool"""
        test_event_data = {
            "event_type": "typhoon",
            "historical_frequency": 0.15,
            "confidence_level": 0.9
        }
        
        result = await calculate_loss_ratio.ainvoke({"event_data": test_event_data})
        
        assert isinstance(result, float)
        assert 0 <= result <= 1
    
    @pytest.mark.asyncio
    async def test_calculate_loss_ratio_empty_data(self):
        """Test calculate_loss_ratio with empty data"""
        result = await calculate_loss_ratio.ainvoke({"event_data": {}})
        assert result == 0.0


class TestPlannerNode:
    """Test planner node"""
    
    def test_extract_event_type(self):
        """Test event type extraction"""
        test_cases = [
            ("태풍 손해율 계산", "typhoon"),
            ("항공편 지연 보험", "flight_delay"),
            ("지진 위험도 분석", "earthquake"),
            ("일반적인 보험", "general")
        ]
        
        for user_input, expected in test_cases:
            result = extract_event_type(user_input)
            assert result == expected
    
    @pytest.mark.asyncio
    async def test_planner_node(self):
        """Test planner node execution"""
        state = {
            "messages": [{"role": "user", "content": "태풍 손해율 계산"}],
            "plan": "",
            "result": None
        }
        
        result = await planner_node(state)
        
        assert "plan" in result
        assert "event_type" in result
        assert result["event_type"] == "typhoon"
        assert len(result["messages"]) > len(state["messages"])


class TestRouterNode:
    """Test router node"""
    
    def test_determine_tools_from_plan(self):
        """Test tool determination from plan"""
        test_plan = "태풍 데이터를 수집하고 손해율을 계산해야 합니다."
        result = determine_tools_from_plan(test_plan, "typhoon")
        
        assert "collect_event_data" in result
        assert "calculate_loss_ratio" in result
    
    @pytest.mark.asyncio
    async def test_tool_router(self):
        """Test tool router execution"""
        state = {
            "messages": [],
            "plan": "태풍 데이터를 수집하고 손해율을 계산하세요.",
            "event_type": "typhoon",
            "result": None
        }
        
        result = await tool_router(state)
        
        assert "tool_calls" in result
        assert "tool_parameters" in result
        assert "collect_event_data" in result["tool_calls"]


class TestExecutorNode:
    """Test executor node"""
    
    @pytest.mark.asyncio
    async def test_executor_layer(self):
        """Test executor layer execution"""
        state = {
            "messages": [],
            "plan": "태풍 손해율 계산",
            "tool_calls": ["collect_event_data", "calculate_loss_ratio"],
            "tool_parameters": {
                "collect_event_data": {"event_type": "typhoon"},
                "calculate_loss_ratio": {"requires_event_data": True}
            },
            "result": None
        }
        
        result = await executor_layer(state)
        
        assert "result" in result
        assert "loss_ratio" in result
        assert isinstance(result["loss_ratio"], float)
        assert 0 <= result["loss_ratio"] <= 1


class TestInsuranceAgent:
    """Test complete insurance agent"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization"""
        agent = InsuranceAgent()
        assert agent.graph is not None
        assert agent.agent is not None
    
    @pytest.mark.asyncio
    async def test_agent_run_success(self):
        """Test successful agent run"""
        agent = InsuranceAgent()
        result = await agent.run("태풍 손해율 계산")
        
        assert result["status"] == "success"
        assert "loss_ratio" in result
        assert isinstance(result["loss_ratio"], float)
    
    @pytest.mark.asyncio
    async def test_run_insurance_agent_function(self):
        """Test convenience function"""
        result = await run_insurance_agent("태풍 손해율 계산")
        
        assert result["status"] == "success"
        assert "loss_ratio" in result
        assert "summary" in result
        assert "event_data" in result
    
    @pytest.mark.asyncio
    async def test_different_event_types(self):
        """Test agent with different event types"""
        test_cases = [
            "태풍 손해율 계산",
            "항공편 지연 보험 설계",
            "지진 위험도 분석"
        ]
        
        for test_input in test_cases:
            result = await run_insurance_agent(test_input)
            assert result["status"] == "success"
            assert "loss_ratio" in result


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """Test complete end-to-end flow"""
        user_input = "태풍으로 인한 손해율을 계산해주세요"
        
        # Run the agent
        result = await run_insurance_agent(user_input)
        
        # Verify results
        assert result["status"] == "success"
        assert "loss_ratio" in result
        assert isinstance(result["loss_ratio"], float)
        assert 0 <= result["loss_ratio"] <= 1
        
        # Verify summary
        assert "summary" in result
        summary = result["summary"]
        assert "event_type" in summary
        assert "risk_level" in summary
        assert "recommendation" in summary
        
        # Verify event data
        assert "event_data" in result
        event_data = result["event_data"]
        assert "historical_frequency" in event_data
        assert "confidence_level" in event_data
    
    @pytest.mark.asyncio
    async def test_performance_requirement(self):
        """Test that execution time is under 10 seconds"""
        import time
        
        start_time = time.time()
        result = await run_insurance_agent("태풍 손해율 계산")
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 10.0, f"Execution time {execution_time:.2f}s exceeds 10s limit"
        assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])