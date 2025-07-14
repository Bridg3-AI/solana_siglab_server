"""
Solana blockchain service for handling blockchain operations
"""
import sys
import os

# Add agents directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Firebase imports
from firebase.core.logging import logger, log_agent_interaction, log_error

try:
    from agents import run_solana_agent
    from agents.memory import create_memory
    AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import agents module: {e}")
    AGENTS_AVAILABLE = False


class SolanaService:
    def __init__(self, firestore_client=None):
        self.db = firestore_client
        self.agents_available = AGENTS_AVAILABLE
    
    def process_agent_request(self, user_input: str, session_id: str = "anonymous", 
                            user_id: str = None, network: str = "mainnet-beta") -> dict:
        """Process a request through the Solana agent"""
        if not self.agents_available:
            return {
                "error": "Agents module not available",
                "response": None,
                "context": {},
                "tools_used": [],
                "iterations": 0
            }
        
        try:
            # Run the agent
            result = run_solana_agent(
                user_input,
                network=network,
                session_id=session_id,
                user_id=user_id,
                max_iterations=10
            )
            
            # Store conversation in Firestore if available
            if self.db and session_id != "anonymous":
                try:
                    memory = create_memory("firestore", firestore_client=self.db)
                    memory.add_message(session_id, "user", user_input)
                    memory.add_message(session_id, "assistant", result["response"])
                except Exception as e:
                    print(f"Failed to save conversation: {e}")
            
            return result
        
        except Exception as e:
            return {
                "error": f"Internal server error: {str(e)}",
                "response": None,
                "context": {"error": True},
                "tools_used": [],
                "iterations": 0
            }
    
    def get_conversation_history(self, session_id: str) -> dict:
        """Get conversation history for a session"""
        try:
            if self.agents_available and self.db:
                memory = create_memory("firestore", firestore_client=self.db)
                conversation = memory.get_conversation(session_id)
                metadata = memory.get_session_metadata(session_id)
            elif self.db:
                # Fallback to direct Firestore query
                doc_ref = self.db.collection("conversations").document(session_id)
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    conversation = data.get("messages", [])
                    metadata = data.get("metadata", {})
                else:
                    conversation = []
                    metadata = {}
            else:
                conversation = []
                metadata = {}
            
            return {
                "session_id": session_id,
                "conversation": conversation,
                "metadata": metadata
            }
        
        except Exception as e:
            return {
                "error": f"Failed to fetch conversation: {str(e)}",
                "session_id": session_id,
                "conversation": [],
                "metadata": {}
            }