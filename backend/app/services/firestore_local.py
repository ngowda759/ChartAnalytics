"""
Firestore Local Fallback Service

Provides local JSON file-based storage as fallback when Firebase is not configured.
This allows development and testing without Firebase credentials.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class FirestoreLocalFallback:
    """
    Local JSON file-based fallback for Firestore.
    Implements the same interface as Firebase/Firestore for easy switching.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Default to backend/data directory
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize data files
        self._init_collections()
        
        self.logger = structlog.get_logger()
        self.logger.info("firestore_local_initialized", data_dir=str(self.data_dir))

    def _init_collections(self):
        """Initialize collection files if they don't exist."""
        collections = [
            "users",
            "trades",
            "strategies",
            "alerts",
            "market_data",
            "options_chain",
        ]
        
        for collection in collections:
            file_path = self.data_dir / f"{collection}.json"
            if not file_path.exists():
                self._save_collection(collection, {})

    def _get_collection_path(self, collection: str) -> Path:
        """Get the file path for a collection."""
        return self.data_dir / f"{collection}.json"

    def _load_collection(self, collection: str) -> Dict[str, Any]:
        """Load a collection from JSON file."""
        file_path = self._get_collection_path(collection)
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_collection(self, collection: str, data: Dict[str, Any]):
        """Save a collection to JSON file."""
        file_path = self._get_collection_path(collection)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return f"{datetime.utcnow().timestamp()}_{os.urandom(4).hex()}"

    # ========== CRUD Operations ==========

    async def add(
        self,
        collection: str,
        data: Dict[str, Any],
        document_id: Optional[str] = None,
    ) -> str:
        """Add a document to a collection."""
        coll = self._load_collection(collection)
        
        doc_id = document_id or self._generate_id()
        data["id"] = doc_id
        data["created_at"] = datetime.utcnow().isoformat()
        data["updated_at"] = datetime.utcnow().isoformat()
        
        coll[doc_id] = data
        self._save_collection(collection, coll)
        
        self.logger.info("document_added", collection=collection, doc_id=doc_id)
        return doc_id

    async def get(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        coll = self._load_collection(collection)
        return coll.get(document_id)

    async def update(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Update a document."""
        coll = self._load_collection(collection)
        
        if document_id not in coll:
            return False
        
        coll[document_id].update(data)
        coll[document_id]["updated_at"] = datetime.utcnow().isoformat()
        self._save_collection(collection, coll)
        
        self.logger.info("document_updated", collection=collection, doc_id=document_id)
        return True

    async def delete(self, collection: str, document_id: str) -> bool:
        """Delete a document."""
        coll = self._load_collection(collection)
        
        if document_id not in coll:
            return False
        
        del coll[document_id]
        self._save_collection(collection, coll)
        
        self.logger.info("document_deleted", collection=collection, doc_id=document_id)
        return True

    async def list(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> List[Dict[str, Any]]:
        """List documents with optional filters."""
        coll = self._load_collection(collection)
        results = list(coll.values())
        
        # Apply filters
        if filters:
            results = [
                doc for doc in results
                if all(doc.get(k) == v for k, v in filters.items())
            ]
        
        # Apply ordering
        if order_by:
            results.sort(
                key=lambda x: x.get(order_by, ""),
                reverse=descending,
            )
        
        # Apply limit
        return results[:limit]

    async def query(
        self,
        collection: str,
        field: str,
        operator: str,
        value: Any,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query documents by field and operator."""
        coll = self._load_collection(collection)
        results = []
        
        for doc in coll.values():
            doc_value = doc.get(field)
            
            if operator == "==" and doc_value == value:
                results.append(doc)
            elif operator == "!=" and doc_value != value:
                results.append(doc)
            elif operator == ">" and doc_value is not None and doc_value > value:
                results.append(doc)
            elif operator == ">=" and doc_value is not None and doc_value >= value:
                results.append(doc)
            elif operator == "<" and doc_value is not None and doc_value < value:
                results.append(doc)
            elif operator == "<=" and doc_value is not None and doc_value <= value:
                results.append(doc)
            elif operator == "in" and doc_value in value:
                results.append(doc)
            elif operator == "array_contains" and value in doc_value:
                results.append(doc)
        
        return results[:limit]

    # ========== Batch Operations ==========

    async def batch_add(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """Add multiple documents in a batch."""
        coll = self._load_collection(collection)
        doc_ids = []
        
        for data in documents:
            doc_id = self._generate_id()
            data["id"] = doc_id
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = datetime.utcnow().isoformat()
            coll[doc_id] = data
            doc_ids.append(doc_id)
        
        self._save_collection(collection, coll)
        self.logger.info("batch_add_completed", collection=collection, count=len(doc_ids))
        return doc_ids

    async def batch_delete(self, collection: str, document_ids: List[str]) -> int:
        """Delete multiple documents in a batch."""
        coll = self._load_collection(collection)
        deleted = 0
        
        for doc_id in document_ids:
            if doc_id in coll:
                del coll[doc_id]
                deleted += 1
        
        self._save_collection(collection, coll)
        self.logger.info("batch_delete_completed", collection=collection, count=deleted)
        return deleted

    # ========== Aggregation ==========

    async def count(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents in a collection."""
        results = await self.list(collection, filters=filters, limit=10000)
        return len(results)

    async def exists(self, collection: str, document_id: str) -> bool:
        """Check if a document exists."""
        doc = await self.get(collection, document_id)
        return doc is not None


# Singleton instance
firestore_local = FirestoreLocalFallback()
