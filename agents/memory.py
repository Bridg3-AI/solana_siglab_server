from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os


class ConversationMemory:
    """Local conversation memory implementation"""
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
            self.metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "message_count": 0
            }
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversations[session_id].append(message)
        
        # Keep only the last max_messages
        if len(self.conversations[session_id]) > self.max_messages:
            self.conversations[session_id] = self.conversations[session_id][-self.max_messages:]
        
        # Update metadata
        self.metadata[session_id]["last_updated"] = datetime.now().isoformat()
        self.metadata[session_id]["message_count"] = len(self.conversations[session_id])
    
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get full conversation history for a session"""
        return self.conversations.get(session_id, [])
    
    def get_recent_messages(self, session_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from conversation"""
        conversation = self.get_conversation(session_id)
        return conversation[-count:] if conversation else []
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
        if session_id in self.metadata:
            del self.metadata[session_id]
    
    def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Get metadata for a session"""
        return self.metadata.get(session_id, {})
    
    def list_sessions(self) -> List[str]:
        """List all active sessions"""
        return list(self.conversations.keys())
    
    def export_conversation(self, session_id: str) -> Dict[str, Any]:
        """Export conversation to dict format"""
        return {
            "session_id": session_id,
            "metadata": self.get_session_metadata(session_id),
            "messages": self.get_conversation(session_id)
        }
    
    def save_to_file(self, session_id: str, filepath: str):
        """Save conversation to file"""
        data = self.export_conversation(session_id)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Load conversation from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            session_id = data["session_id"]
            self.metadata[session_id] = data["metadata"]
            self.conversations[session_id] = data["messages"]


class FirestoreMemory:
    """Firestore-based conversation memory implementation"""
    
    def __init__(self, firestore_client, collection_name: str = "conversations", max_messages: int = 50):
        self.db = firestore_client
        self.collection_name = collection_name
        self.max_messages = max_messages
        self.local_cache = ConversationMemory(max_messages)
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add message to both local cache and Firestore"""
        # Add to local cache first
        self.local_cache.add_message(session_id, role, content, metadata)
        
        # Save to Firestore
        try:
            self._save_to_firestore(session_id)
        except Exception as e:
            print(f"Failed to save to Firestore: {e}")
    
    def _save_to_firestore(self, session_id: str):
        """Save conversation to Firestore"""
        doc_ref = self.db.collection(self.collection_name).document(session_id)
        doc_ref.set({
            "messages": self.local_cache.conversations[session_id],
            "metadata": self.local_cache.metadata[session_id],
            "updated_at": datetime.now()
        })
    
    def _load_from_firestore(self, session_id: str):
        """Load conversation from Firestore"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                self.local_cache.conversations[session_id] = data.get("messages", [])
                self.local_cache.metadata[session_id] = data.get("metadata", {})
        except Exception as e:
            print(f"Failed to load from Firestore: {e}")
    
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation, loading from Firestore if not in cache"""
        if session_id not in self.local_cache.conversations:
            self._load_from_firestore(session_id)
        
        return self.local_cache.get_conversation(session_id)
    
    def get_recent_messages(self, session_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages"""
        conversation = self.get_conversation(session_id)
        return conversation[-count:] if conversation else []
    
    def clear_conversation(self, session_id: str):
        """Clear conversation from both cache and Firestore"""
        self.local_cache.clear_conversation(session_id)
        
        try:
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc_ref.delete()
        except Exception as e:
            print(f"Failed to delete from Firestore: {e}")
    
    def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Get session metadata"""
        if session_id not in self.local_cache.metadata:
            self._load_from_firestore(session_id)
        
        return self.local_cache.get_session_metadata(session_id)
    
    def list_sessions(self) -> List[str]:
        """List all sessions from Firestore"""
        try:
            docs = self.db.collection(self.collection_name).stream()
            return [doc.id for doc in docs]
        except Exception as e:
            print(f"Failed to list sessions: {e}")
            return self.local_cache.list_sessions()


def create_memory(memory_type: str = "local", **kwargs):
    """Factory function to create memory instance"""
    if memory_type == "local":
        max_messages = kwargs.get("max_messages", 50)
        return ConversationMemory(max_messages)
    
    elif memory_type == "firestore":
        firestore_client = kwargs.get("firestore_client")
        collection_name = kwargs.get("collection_name", "conversations")
        max_messages = kwargs.get("max_messages", 50)
        
        if not firestore_client:
            raise ValueError("firestore_client is required for Firestore memory")
        
        return FirestoreMemory(firestore_client, collection_name, max_messages)
    
    else:
        raise ValueError(f"Unsupported memory type: {memory_type}")