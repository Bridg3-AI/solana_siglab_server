from typing import Dict, Any, Optional, Callable
import json
import requests
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class SolanaBalanceTool(BaseTool):
    name: str = "get_solana_balance"
    description: str = "Get SOL balance for a Solana address"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    def _run(self, address: str) -> str:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [address]
        }
        
        try:
            response = requests.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "result" in result:
                lamports = result["result"]["value"]
                sol_balance = lamports / 1_000_000_000
                return f"Balance: {sol_balance:.9f} SOL ({lamports} lamports)"
            else:
                return f"Error: {result.get('error', 'Unknown error')}"
        
        except Exception as e:
            return f"Failed to get balance: {str(e)}"


class SolanaTransactionTool(BaseTool):
    name: str = "get_transaction_info"
    description: str = "Get information about a Solana transaction by signature"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    def _run(self, signature: str) -> str:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        }
        
        try:
            response = requests.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "result" in result and result["result"]:
                tx_data = result["result"]
                status = "success" if tx_data["meta"]["err"] is None else "failed"
                fee = tx_data["meta"]["fee"] if tx_data.get("meta") else "unknown"
                slot = tx_data.get("slot", "unknown")
                
                return f"Transaction Status: {status}, Slot: {slot}, Fee: {fee} lamports"
            else:
                return "Transaction not found"
        
        except Exception as e:
            return f"Failed to get transaction info: {str(e)}"


class SolanaSignatureValidatorTool(BaseTool):
    name: str = "validate_signature"
    description: str = "Validate if a Solana signature exists on the blockchain"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    def _run(self, signature: str) -> str:
        try:
            if len(signature) < 64 or len(signature) > 88:
                return "Invalid signature format"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[signature]]
            }
            
            response = requests.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "result" in result:
                statuses = result["result"]["value"]
                is_valid = statuses[0] is not None
                return f"Signature is {'valid' if is_valid else 'invalid'}"
            
            return "Unable to validate signature"
        
        except Exception as e:
            return f"Validation error: {str(e)}"


class SolanaAccountInfoTool(BaseTool):
    name: str = "get_account_info"
    description: str = "Get account information for a Solana address"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    def _run(self, address: str) -> str:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                address,
                {
                    "encoding": "jsonParsed"
                }
            ]
        }
        
        try:
            response = requests.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "result" in result and result["result"]["value"]:
                account_data = result["result"]["value"]
                return json.dumps({
                    "lamports": account_data["lamports"],
                    "owner": account_data["owner"],
                    "executable": account_data["executable"],
                    "rentEpoch": account_data["rentEpoch"]
                }, indent=2)
            else:
                return "Account not found or has no data"
        
        except Exception as e:
            return f"Failed to get account info: {str(e)}"


def get_solana_tools(rpc_url: str = "https://api.mainnet-beta.solana.com") -> list:
    """Get list of available Solana tools"""
    tools = [
        SolanaBalanceTool(rpc_url=rpc_url),
        SolanaTransactionTool(rpc_url=rpc_url),
        SolanaSignatureValidatorTool(rpc_url=rpc_url),
        SolanaAccountInfoTool(rpc_url=rpc_url)
    ]
    return tools


def get_tool_by_name(name: str, rpc_url: str = "https://api.mainnet-beta.solana.com") -> Optional[BaseTool]:
    """Get a specific tool by name"""
    tools_map = {
        "get_solana_balance": SolanaBalanceTool(rpc_url=rpc_url),
        "get_transaction_info": SolanaTransactionTool(rpc_url=rpc_url),
        "validate_signature": SolanaSignatureValidatorTool(rpc_url=rpc_url),
        "get_account_info": SolanaAccountInfoTool(rpc_url=rpc_url)
    }
    return tools_map.get(name)