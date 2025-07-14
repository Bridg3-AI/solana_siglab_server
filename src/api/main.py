from firebase_functions import https_fn, firestore_fn
from firebase_functions.options import set_global_options
import sys
import os
from typing import Dict, Any
import time

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Firebase imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from firebase import get_db, firebase_app, AuthMiddleware
from firebase.core.logging import logger, log_function_call, log_performance, log_error
from firebase.core.exceptions import ValidationError, AuthenticationError, ServiceUnavailableError

# Application imports
from config.settings import settings
from services.solana_service import SolanaService
from services.user_service import UserService
from models.agent import AgentRequest, AgentResponse, HealthCheck
from models.user import CreateUserRequest
from utils.response import ResponseBuilder
from utils.validation import Validator

# Cold start optimization - global configuration
set_global_options(
    max_instances=settings.MAX_INSTANCES,
    memory=512,  # MB - optimize for agent operations
    timeout_sec=60,  # seconds - for agent processing
    concurrency=10  # requests per instance
)

# Global service instances (cold start optimization)
_solana_service = None
_user_service = None

def get_services() -> tuple[SolanaService, UserService]:
    """Get or initialize services (singleton pattern for cold start optimization)"""
    global _solana_service, _user_service
    
    if _solana_service is None or _user_service is None:
        db = get_db()
        _solana_service = SolanaService(db)
        _user_service = UserService(db)
        logger.info("Services initialized", 
                   solana_available=_solana_service.agents_available)
    
    return _solana_service, _user_service

@https_fn.on_request()
def hello_world(req: https_fn.Request) -> https_fn.Response:
    return ResponseBuilder.success({
        "message": "Hello from Solana SigLab Server!",
        "agents_available": solana_service.agents_available,
        "version": "1.0.0"
    })

@https_fn.on_request()
def health_check(req: https_fn.Request) -> https_fn.Response:
    health_data = HealthCheck(
        status="healthy",
        timestamp=str(firestore.SERVER_TIMESTAMP),
        agents_available=solana_service.agents_available,
        services={
            "firebase": True,
            "firestore": True,
            "agents": solana_service.agents_available
        }
    )
    return ResponseBuilder.success(health_data.dict())

@https_fn.on_request()
def solana_agent(req: https_fn.Request) -> https_fn.Response:
    """Solana agent endpoint for blockchain queries"""
    if not AGENTS_AVAILABLE:
        return https_fn.Response(
            json.dumps({"error": "Agents module not available"}),
            status=503,
            headers={"Content-Type": "application/json"}
        )
    
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)
    
    try:
        # Parse request data
        request_data = req.get_json()
        if not request_data:
            return https_fn.Response(
                json.dumps({"error": "No JSON data provided"}),
                status=400,
                headers={"Content-Type": "application/json"}
            )
        
        user_input = request_data.get("message", "")
        session_id = request_data.get("session_id", "anonymous")
        user_id = request_data.get("user_id")
        network = request_data.get("network", "mainnet-beta")
        
        if not user_input:
            return https_fn.Response(
                json.dumps({"error": "Message is required"}),
                status=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Run the agent
        result = run_solana_agent(
            user_input,
            network=network,
            session_id=session_id,
            user_id=user_id,
            max_iterations=10
        )
        
        # Store conversation in Firestore if session_id provided
        if session_id != "anonymous":
            try:
                memory = create_memory("firestore", firestore_client=db)
                memory.add_message(session_id, "user", user_input)
                memory.add_message(session_id, "assistant", result["response"])
            except Exception as e:
                print(f"Failed to save conversation: {e}")
        
        return https_fn.Response(
            json.dumps({
                "response": result["response"],
                "context": result["context"],
                "tools_used": result["tools_used"],
                "iterations": result["iterations"],
                "intent": result["intent"],
                "session_id": session_id
            }),
            headers={"Content-Type": "application/json"}
        )
    
    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status=500,
            headers={"Content-Type": "application/json"}
        )

@https_fn.on_request()
def api_users(req: https_fn.Request) -> https_fn.Response:
    """User management API"""
    if req.method == "GET":
        try:
            users_ref = db.collection("users")
            users = []
            for doc in users_ref.stream():
                user_data = doc.to_dict()
                user_data["id"] = doc.id
                users.append(user_data)
            
            return https_fn.Response(
                json.dumps({"users": users}),
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            return https_fn.Response(
                json.dumps({"error": f"Failed to fetch users: {str(e)}"}),
                status=500,
                headers={"Content-Type": "application/json"}
            )
    
    elif req.method == "POST":
        try:
            user_data = req.get_json()
            if not user_data:
                return https_fn.Response(
                    json.dumps({"error": "No user data provided"}),
                    status=400,
                    headers={"Content-Type": "application/json"}
                )
            
            # Add timestamp
            user_data["created_at"] = firestore.SERVER_TIMESTAMP
            user_data["updated_at"] = firestore.SERVER_TIMESTAMP
            
            # Add to Firestore
            doc_ref = db.collection("users").add(user_data)
            
            return https_fn.Response(
                json.dumps({
                    "message": "User created successfully",
                    "user_id": doc_ref[1].id
                }),
                headers={"Content-Type": "application/json"},
                status=201
            )
        except Exception as e:
            return https_fn.Response(
                json.dumps({"error": f"Failed to create user: {str(e)}"}),
                status=500,
                headers={"Content-Type": "application/json"}
            )
    
    else:
        return https_fn.Response("Method not allowed", status=405)

@https_fn.on_request()
def conversation_history(req: https_fn.Request) -> https_fn.Response:
    """Get conversation history for a session"""
    if req.method != "GET":
        return https_fn.Response("Method not allowed", status=405)
    
    session_id = req.args.get("session_id")
    if not session_id:
        return https_fn.Response(
            json.dumps({"error": "session_id parameter is required"}),
            status=400,
            headers={"Content-Type": "application/json"}
        )
    
    try:
        if AGENTS_AVAILABLE:
            memory = create_memory("firestore", firestore_client=db)
            conversation = memory.get_conversation(session_id)
            metadata = memory.get_session_metadata(session_id)
        else:
            # Fallback to direct Firestore query
            doc_ref = db.collection("conversations").document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                conversation = data.get("messages", [])
                metadata = data.get("metadata", {})
            else:
                conversation = []
                metadata = {}
        
        return https_fn.Response(
            json.dumps({
                "session_id": session_id,
                "conversation": conversation,
                "metadata": metadata
            }),
            headers={"Content-Type": "application/json"}
        )
    
    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": f"Failed to fetch conversation: {str(e)}"}),
            status=500,
            headers={"Content-Type": "application/json"}
        )

@firestore_fn.on_document_created(document="users/{user_id}")
def on_user_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot]) -> None:
    """Triggered when a new user is created"""
    user_id = event.params['user_id']
    user_data = event.data.to_dict()
    print(f"User created: {user_id}, data: {user_data}")

@firestore_fn.on_document_updated(document="users/{user_id}")
def on_user_updated(event: firestore_fn.Event[firestore_fn.Change[firestore_fn.DocumentSnapshot]]) -> None:
    """Triggered when a user is updated"""
    user_id = event.params['user_id']
    before_data = event.data.before.to_dict() if event.data.before else {}
    after_data = event.data.after.to_dict() if event.data.after else {}
    print(f"User updated: {user_id}, before: {before_data}, after: {after_data}")

@firestore_fn.on_document_created(document="conversations/{session_id}")
def on_conversation_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot]) -> None:
    """Triggered when a new conversation is created"""
    session_id = event.params['session_id']
    conversation_data = event.data.to_dict()
    print(f"Conversation created: {session_id}, messages: {len(conversation_data.get('messages', []))}")