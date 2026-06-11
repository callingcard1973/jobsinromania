#!/usr/bin/env python3
from app.core.analytics import Analytics
from typing import Optional, Dict, Any
from datetime import datetime, timezone

class DocumentTracker:
    DOCUMENT_TYPES = {
        "ad": "classified_ad",
        "user": "user_profile",
        "media": "media_attachment",
        "message": "user_message",
        "review": "user_review",
    }

    @staticmethod
    def mark_document_created(doc_type: str, doc_id: int, user_id: str, properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        Analytics.track_user_action(user_id, f"document_{doc_type}_created", props)

    @staticmethod
    def mark_document_viewed(doc_type: str, doc_id: int, user_id: Optional[str], properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "viewed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        uid = user_id or "anonymous"
        Analytics.track_user_action(uid, f"document_{doc_type}_viewed", props)

    @staticmethod
    def mark_document_edited(doc_type: str, doc_id: int, user_id: str, properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "edited",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        Analytics.track_user_action(user_id, f"document_{doc_type}_edited", props)

    @staticmethod
    def mark_document_deleted(doc_type: str, doc_id: int, user_id: str, properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "deleted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        Analytics.track_user_action(user_id, f"document_{doc_type}_deleted", props)

    @staticmethod
    def mark_document_shared(doc_type: str, doc_id: int, user_id: str, shared_with: str, properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "shared",
            "shared_with": shared_with,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        Analytics.track_user_action(user_id, f"document_{doc_type}_shared", props)

    @staticmethod
    def mark_document_published(doc_type: str, doc_id: int, user_id: str, properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "published",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        Analytics.track_user_action(user_id, f"document_{doc_type}_published", props)

    @staticmethod
    def mark_document_archived(doc_type: str, doc_id: int, user_id: str, properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "action": "archived",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        Analytics.track_user_action(user_id, f"document_{doc_type}_archived", props)

    @staticmethod
    def mark_document_searched(search_query: str, doc_type: str, results_count: int, user_id: Optional[str], properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "search_query": search_query,
            "results_count": results_count,
            "action": "searched",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        uid = user_id or "anonymous"
        Analytics.track_user_action(uid, f"document_{doc_type}_search", props)

    @staticmethod
    def mark_document_filtered(doc_type: str, filters: Dict, results_count: int, user_id: Optional[str], properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "filters_applied": list(filters.keys()),
            "results_count": results_count,
            "action": "filtered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        uid = user_id or "anonymous"
        Analytics.track_user_action(uid, f"document_{doc_type}_filter", props)

    @staticmethod
    def mark_document_interaction(doc_type: str, doc_id: int, interaction_type: str, user_id: Optional[str], properties: Optional[Dict] = None):
        props = properties or {}
        props.update({
            "document_type": DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type),
            "document_id": doc_id,
            "interaction_type": interaction_type,
            "action": "interacted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        uid = user_id or "anonymous"
        Analytics.track_user_action(uid, f"document_{doc_type}_{interaction_type}", props)

    @staticmethod
    def get_document_mark(doc_type: str, doc_id: int, action: str) -> str:
        return f"doc_{DocumentTracker.DOCUMENT_TYPES.get(doc_type, doc_type)}_{doc_id}_{action}"
