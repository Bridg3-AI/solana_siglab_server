#!/usr/bin/env python3
"""
CLI entry point for Insurance Agent V0.1
Usage: python run_agent.py "태풍 손해율 계산"
"""
import sys
import asyncio
import json
import os
from typing import Dict, Any

# Add the src directory to the path so we can import from agents
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env file
from agents.core.config import load_env_file, get_config
load_env_file()

from agents.insurance_agent import run_insurance_agent


async def main():
    """Main CLI function"""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py \"<user_input>\"")
        print("Example: python run_agent.py \"태풍 손해율 계산\"")
        sys.exit(1)
    
    user_input = sys.argv[1]
    
    try:
        # Run the insurance agent
        print(f"Processing: {user_input}")
        print("=" * 50)
        
        result = await run_insurance_agent(user_input)
        
        # Format and display results
        if result.get("status") == "success":
            print("✅ Agent execution completed successfully!")
            print()
            
            # Display loss ratio (main requirement)
            if "loss_ratio" in result:
                print(f"Loss Ratio: {result['loss_ratio']}")
                print()
            
            # Display summary if available
            if "summary" in result:
                summary = result["summary"]
                print("📊 Summary:")
                print(f"  Event Type: {summary.get('event_type', 'N/A')}")
                print(f"  Risk Level: {summary.get('risk_level', 'N/A')}")
                print(f"  Recommendation: {summary.get('recommendation', 'N/A')}")
                print()
            
            # Display event data if available
            if "event_data" in result:
                event_data = result["event_data"]
                print("📈 Event Data:")
                print(f"  Historical Frequency: {event_data.get('historical_frequency', 'N/A')}")
                print(f"  Confidence Level: {event_data.get('confidence_level', 'N/A')}")
                print(f"  Data Source: {event_data.get('data_source', 'N/A')}")
                print()
            
            # JSON output for programmatic use
            print("📋 JSON Output:")
            json_output = {"loss_ratio": result.get("loss_ratio")}
            print(json.dumps(json_output, indent=2, ensure_ascii=False))
            
        else:
            print("❌ Agent execution failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Execution cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)


def display_help():
    """Display help information"""
    help_text = """
Solana SigLab Insurance Agent V0.1
==================================

Usage:
    python run_agent.py "<user_input>"

Examples:
    python run_agent.py "태풍 손해율 계산"
    python run_agent.py "항공편 지연 관련 보험을 만들어줘"
    python run_agent.py "지진 위험도 분석"

Features:
    - Natural language processing for insurance requests
    - Event data collection (mock implementation)
    - Loss ratio calculation
    - Risk assessment and recommendations

Output:
    - Loss ratio (float between 0.0 and 1.0)
    - Risk level classification
    - Recommendations
    - JSON format for programmatic use

Requirements:
    - Python 3.11+
    - OpenAI API key (set as OPENAI_API_KEY environment variable)
    - Required packages: langgraph, langchain, openai, pydantic
"""
    print(help_text)


if __name__ == "__main__":
    # Handle help requests
    if len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help", "help"]:
        display_help()
        sys.exit(0)
    
    # Check configuration
    try:
        config = get_config()
        if not config.validate():
            raise ValueError("Invalid configuration")
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print()
        print("Please ensure:")
        print("1. Set OPENAI_API_KEY environment variable:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print()
        print("2. Or create a .env file with:")
        print("   OPENAI_API_KEY=your-api-key-here")
        print()
        print("3. Check .env.example for all available settings")
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main())