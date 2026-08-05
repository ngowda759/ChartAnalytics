"""
Database Service - Unified interface for Firestore with local fallback.

This module provides a unified database interface that:
1. Uses Firebase/Firestore when configured
2. Falls back to local JSON files for development/testing
3. Provides the same interface for both backends
"""
import os
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class DatabaseService:
    """
    Unified database service with Firebase/Firestore backend and local JSON fallback.
    """

    def __init__(self):
        self.logger = structlog.get_logger()
        self._use_firebase = self._check_firebase_config()
        
        if self._use_firebase:
            self.logger.info("Using Firebase/Firestore as database backend")
            from app.services.firebase import db as firebase_db
            self._db = firebase_db
        else:
            self.logger.info("Using local JSON fallback for database")
            from app.services.firestore_local import firestore_local
            self._db = firestore_local

    def _check_firebase_config(self) -> bool:
        """Check if Firebase is properly configured."""
        # Check for required environment variables
        required_vars = [
            "FIREBASE_PROJECT_ID",
            "FIREBASE_PRIVATE_KEY",
            "FIREBASE_CLIENT_EMAIL",
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                self.logger.warning("firebase_not_configured", missing_var=var)
                return False
        
        # Check if GOOGLE_APPLICATION_CREDENTIALS or credentials are available
        if not os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")):
            if not os.getenv("FIREBASE_PRIVATE_KEY"):
                return False
        
        return True

    # ========== CRUD Operations ==========

    async def add(
        self,
        collection: str,
        data: Dict[str, Any],
        document_id: Optional[str] = None,
    ) -> str:
        """Add a document to a collection."""
        return await self._db.add(collection, data, document_id)

    async def get(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        return await self._db.get(collection, document_id)

    async def update(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Update a document."""
        return await self._db.update(collection, document_id, data)

    async def delete(self, collection: str, document_id: str) -> bool:
        """Delete a document."""
        return await self._db.delete(collection, document_id)

    async def list(
        self,
        collection: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> List[Dict[str, Any]]:
        """List documents with optional filters."""
        return await self._db.list(collection, filters, limit, order_by, descending)

    async def query(
        self,
        collection: str,
        field: str,
        operator: str,
        value: Any,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query documents by field and operator."""
        return await self._db.query(collection, field, operator, value, limit)

    # ========== Batch Operations ==========

    async def batch_add(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
    ) -> List[str]:
        """Add multiple documents in a batch."""
        return await self._db.batch_add(collection, documents)

    async def batch_delete(self, collection: str, document_ids: List[str]) -> int:
        """Delete multiple documents in a batch."""
        return await self._db.batch_delete(collection, document_ids)

    # ========== Aggregation ==========

    async def count(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents in a collection."""
        return await self._db.count(collection, filters)

    async def exists(self, collection: str, document_id: str) -> bool:
        """Check if a document exists."""
        return await self._db.exists(collection, document_id)

    # ========== Helper Methods ==========

    @property
    def is_using_firebase(self) -> bool:
        """Check if using Firebase backend."""
        return self._use_firebase

    @property
    def backend_name(self) -> str:
        """Get the name of the backend in use."""
        return "Firebase/Firestore" if self._use_firebase else "Local JSON (Fallback)"


# Singleton instance
db = DatabaseService()
