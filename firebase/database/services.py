"""
Firestore database services
"""
from typing import Dict, Any, List, Optional
from firebase_admin import firestore
from ..core.logging import logger, log_error


class FirestoreService:
    """Enhanced Firestore service with common operations"""
    
    def __init__(self, client: firestore.Client):
        self.db = client
    
    def create_document(self, collection: str, document_id: str = None, data: Dict[str, Any] = None) -> str:
        """Create a new document"""
        try:
            # Add timestamp
            data = data or {}
            data["created_at"] = firestore.SERVER_TIMESTAMP
            data["updated_at"] = firestore.SERVER_TIMESTAMP
            
            if document_id:
                doc_ref = self.db.collection(collection).document(document_id)
                doc_ref.set(data)
                return document_id
            else:
                doc_ref = self.db.collection(collection).add(data)
                return doc_ref[1].id
                
        except Exception as e:
            log_error(e, context="create_document", collection=collection)
            raise
    
    def get_document(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            doc_ref = self.db.collection(collection).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data["id"] = doc.id
                return data
            return None
            
        except Exception as e:
            log_error(e, context="get_document", collection=collection, document_id=document_id)
            raise
    
    def update_document(self, collection: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Update a document"""
        try:
            data["updated_at"] = firestore.SERVER_TIMESTAMP
            doc_ref = self.db.collection(collection).document(document_id)
            doc_ref.update(data)
            return True
            
        except Exception as e:
            log_error(e, context="update_document", collection=collection, document_id=document_id)
            raise
    
    def delete_document(self, collection: str, document_id: str) -> bool:
        """Delete a document"""
        try:
            doc_ref = self.db.collection(collection).document(document_id)
            doc_ref.delete()
            return True
            
        except Exception as e:
            log_error(e, context="delete_document", collection=collection, document_id=document_id)
            raise
    
    def query_collection(self, collection: str, filters: List[tuple] = None, 
                         order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Query a collection with filters"""
        try:
            query = self.db.collection(collection)
            
            # Apply filters
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Apply ordering
            if order_by:
                query = query.order_by(order_by)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            return results
            
        except Exception as e:
            log_error(e, context="query_collection", collection=collection)
            raise
    
    def batch_write(self, operations: List[Dict[str, Any]]) -> bool:
        """Perform batch write operations"""
        try:
            batch = self.db.batch()
            
            for operation in operations:
                op_type = operation["type"]  # create, update, delete
                collection = operation["collection"]
                document_id = operation["document_id"]
                doc_ref = self.db.collection(collection).document(document_id)
                
                if op_type == "create":
                    data = operation["data"]
                    data["created_at"] = firestore.SERVER_TIMESTAMP
                    data["updated_at"] = firestore.SERVER_TIMESTAMP
                    batch.set(doc_ref, data)
                
                elif op_type == "update":
                    data = operation["data"]
                    data["updated_at"] = firestore.SERVER_TIMESTAMP
                    batch.update(doc_ref, data)
                
                elif op_type == "delete":
                    batch.delete(doc_ref)
            
            batch.commit()
            return True
            
        except Exception as e:
            log_error(e, context="batch_write", operations_count=len(operations))
            raise
    
    def get_collection_count(self, collection: str, filters: List[tuple] = None) -> int:
        """Get count of documents in collection"""
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Use count aggregation (more efficient)
            count_query = query.count()
            result = count_query.get()
            return result[0][0].value
            
        except Exception as e:
            log_error(e, context="get_collection_count", collection=collection)
            # Fallback to manual count
            docs = self.query_collection(collection, filters)
            return len(docs)
    
    def subcollection_operations(self, parent_collection: str, parent_id: str, 
                                subcollection: str) -> 'FirestoreService':
        """Get a service instance for subcollection operations"""
        # This would return a new service instance configured for subcollections
        # For now, we'll use the same instance
        return self