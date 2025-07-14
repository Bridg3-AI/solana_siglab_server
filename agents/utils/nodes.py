from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .state import AgentState, SolanaAgentState
from .tools import get_solana_tools, get_tool_by_name
import re
import json


def think_node(state: SolanaAgentState) -> SolanaAgentState:
    """Thinking node - analyzes the input and determines intent"""
    state["current_step"] = "thinking"
    
    # Get the last human message
    human_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    if not human_messages:
        state["intent"] = "no_input"
        return state
    
    last_message = human_messages[-1].content.lower()
    
    # Intent classification
    if any(keyword in last_message for keyword in ["balance", "bal", "how much"]):
        state["intent"] = "check_balance"
    elif any(keyword in last_message for keyword in ["transaction", "tx", "transfer"]):
        state["intent"] = "transaction_info"
    elif any(keyword in last_message for keyword in ["signature", "sig", "verify", "validate"]):
        state["intent"] = "verify_signature"
    elif any(keyword in last_message for keyword in ["account", "info", "details"]):
        state["intent"] = "account_info"
    else:
        state["intent"] = "general_query"
    
    # Extract Solana addresses, signatures, or transaction hashes
    address_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    matches = re.findall(address_pattern, human_messages[-1].content)
    
    if matches:
        state["solana_context"]["extracted_address"] = matches[0]
    
    return state


def act_node(state: SolanaAgentState) -> SolanaAgentState:
    """Action node - executes the appropriate tool based on intent"""
    state["current_step"] = "acting"
    state["iteration_count"] += 1
    
    intent = state.get("intent", "general_query")
    extracted_address = state["solana_context"].get("extracted_address")
    
    response = ""
    tool_used = None
    
    try:
        if intent == "check_balance" and extracted_address:
            tool = get_tool_by_name("get_solana_balance", state["rpc_url"])
            response = tool._run(extracted_address)
            tool_used = "get_solana_balance"
            state["solana_context"]["last_balance_check"] = extracted_address
        
        elif intent == "transaction_info" and extracted_address:
            tool = get_tool_by_name("get_transaction_info", state["rpc_url"])
            response = tool._run(extracted_address)
            tool_used = "get_transaction_info"
            state["solana_context"]["last_transaction"] = extracted_address
        
        elif intent == "verify_signature" and extracted_address:
            tool = get_tool_by_name("validate_signature", state["rpc_url"])
            response = tool._run(extracted_address)
            tool_used = "validate_signature"
        
        elif intent == "account_info" and extracted_address:
            tool = get_tool_by_name("get_account_info", state["rpc_url"])
            response = tool._run(extracted_address)
            tool_used = "get_account_info"
        
        else:
            response = handle_general_query(state)
    
    except Exception as e:
        response = f"Error executing action: {str(e)}"
    
    # Add AI response to messages
    state["messages"].append(AIMessage(content=response))
    
    if tool_used:
        state["tools_used"].append(tool_used)
    
    return state


def observe_node(state: SolanaAgentState) -> SolanaAgentState:
    """Observation node - evaluates the result and determines next steps"""
    state["current_step"] = "observing"
    
    # Check if we have a response
    ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
    if ai_messages:
        last_response = ai_messages[-1].content
        
        # Check for errors or incomplete responses
        if "error" in last_response.lower() or "failed" in last_response.lower():
            state["context"]["needs_retry"] = True
        else:
            state["context"]["task_completed"] = True
    
    return state


def should_continue(state: SolanaAgentState) -> str:
    """Conditional edge function to determine if the agent should continue"""
    
    # Check iteration limit
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    
    # Check if task is completed
    if state["context"].get("task_completed", False):
        return "end"
    
    # Check for final answer indicators
    ai_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage)]
    if ai_messages:
        last_response = ai_messages[-1].content.lower()
        if any(phrase in last_response for phrase in ["final answer", "completed", "done"]):
            return "end"
    
    # Check if we need to retry due to errors
    if state["context"].get("needs_retry", False) and state["iteration_count"] < 3:
        state["context"]["needs_retry"] = False
        return "continue"
    
    return "continue"


def handle_general_query(state: SolanaAgentState) -> str:
    """Handle general queries that don't require specific tools"""
    human_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
    if not human_messages:
        return "Hello! I'm a Solana agent. I can help you with balance checks, transaction info, signature validation, and account information."
    
    query = human_messages[-1].content
    
    # Provide helpful guidance
    if "help" in query.lower():
        return """I can help you with:
        - Check balance: Provide a Solana address
        - Transaction info: Provide a transaction signature
        - Signature validation: Provide a signature to verify
        - Account info: Provide an address for detailed account information
        
        Just send me an address or signature and tell me what you'd like to know!"""
    
    # Extract if there's an address but no clear intent
    address_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    matches = re.findall(address_pattern, query)
    
    if matches:
        return f"""I found this address: {matches[0]}
        
        What would you like me to do with it?
        - Check balance
        - Get account information
        - Or something else?"""
    
    return f"I understand you're asking about: {query}\n\nPlease provide a Solana address or signature, and let me know what information you need."


def create_system_message() -> SystemMessage:
    """Create a system message for the agent"""
    return SystemMessage(content="""You are a Solana blockchain assistant agent. You can:

1. Check SOL balances for any Solana address
2. Get transaction information using transaction signatures
3. Validate signatures on the Solana blockchain
4. Get detailed account information

You operate using a think-act-observe pattern:
- Think: Analyze the user's request and determine intent
- Act: Execute the appropriate blockchain query
- Observe: Evaluate results and determine next steps

Always be helpful and provide clear, accurate information about Solana blockchain data.""")