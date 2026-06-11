#!/usr/bin/env python3
import pytest
from unittest.mock import Mock, patch, call
from datetime import timezone
from app.core.document_tracking import DocumentTracker
from app.core.analytics import Analytics

@pytest.fixture
def mock_analytics():
    with patch('app.core.document_tracking.Analytics') as mock:
        yield mock

class TestDocumentTracker:
    def test_document_types_mapping(self):
        assert DocumentTracker.DOCUMENT_TYPES['ad'] == 'classified_ad'
        assert DocumentTracker.DOCUMENT_TYPES['user'] == 'user_profile'
        assert DocumentTracker.DOCUMENT_TYPES['media'] == 'media_attachment'
        assert DocumentTracker.DOCUMENT_TYPES['message'] == 'user_message'
        assert DocumentTracker.DOCUMENT_TYPES['review'] == 'user_review'

    def test_mark_document_created(self, mock_analytics):
        DocumentTracker.mark_document_created('ad', 12345, 'user123', {'category': 'vehicles'})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][0] == 'user123'
        assert call_args[0][1] == 'document_ad_created'

        properties = call_args[0][2]
        assert properties['document_type'] == 'classified_ad'
        assert properties['document_id'] == 12345
        assert properties['action'] == 'created'
        assert properties['category'] == 'vehicles'

    def test_mark_document_viewed(self, mock_analytics):
        DocumentTracker.mark_document_viewed('ad', 12345, 'user456', {'referrer': 'search'})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][0] == 'user456'
        assert call_args[0][1] == 'document_ad_viewed'

        properties = call_args[0][2]
        assert properties['action'] == 'viewed'
        assert properties['referrer'] == 'search'

    def test_mark_document_viewed_anonymous(self, mock_analytics):
        DocumentTracker.mark_document_viewed('ad', 12345, None, {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][0] == 'anonymous'

    def test_mark_document_edited(self, mock_analytics):
        DocumentTracker.mark_document_edited('ad', 12345, 'user123', {'fields_changed': ['price', 'description']})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_edited'

        properties = call_args[0][2]
        assert properties['action'] == 'edited'

    def test_mark_document_deleted(self, mock_analytics):
        DocumentTracker.mark_document_deleted('ad', 12345, 'user123', {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_deleted'

        properties = call_args[0][2]
        assert properties['action'] == 'deleted'

    def test_mark_document_shared(self, mock_analytics):
        DocumentTracker.mark_document_shared('ad', 12345, 'user123', 'facebook', {'shares_count': 5})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_shared'

        properties = call_args[0][2]
        assert properties['action'] == 'shared'
        assert properties['shared_with'] == 'facebook'

    def test_mark_document_published(self, mock_analytics):
        DocumentTracker.mark_document_published('ad', 12345, 'user123', {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_published'

        properties = call_args[0][2]
        assert properties['action'] == 'published'

    def test_mark_document_archived(self, mock_analytics):
        DocumentTracker.mark_document_archived('ad', 12345, 'user123', {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_archived'

        properties = call_args[0][2]
        assert properties['action'] == 'archived'

    def test_mark_document_searched(self, mock_analytics):
        DocumentTracker.mark_document_searched('honda civic', 'ad', 42, 'user456', {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][0] == 'user456'
        assert call_args[0][1] == 'document_ad_search'

        properties = call_args[0][2]
        assert properties['search_query'] == 'honda civic'
        assert properties['results_count'] == 42
        assert properties['action'] == 'searched'

    def test_mark_document_searched_anonymous(self, mock_analytics):
        DocumentTracker.mark_document_searched('search term', 'ad', 10, None, {})

        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][0] == 'anonymous'

    def test_mark_document_filtered(self, mock_analytics):
        filters = {'category': 'vehicles', 'price_max': 5000}
        DocumentTracker.mark_document_filtered('ad', filters, 15, 'user456', {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_filter'

        properties = call_args[0][2]
        assert 'category' in properties['filters_applied']
        assert 'price_max' in properties['filters_applied']
        assert properties['results_count'] == 15
        assert properties['action'] == 'filtered'

    def test_mark_document_interaction(self, mock_analytics):
        DocumentTracker.mark_document_interaction('ad', 12345, 'contact', 'user456', {})

        mock_analytics.track_user_action.assert_called_once()
        call_args = mock_analytics.track_user_action.call_args
        assert call_args[0][1] == 'document_ad_contact'

        properties = call_args[0][2]
        assert properties['interaction_type'] == 'contact'
        assert properties['action'] == 'interacted'

    def test_get_document_mark(self):
        mark = DocumentTracker.get_document_mark('ad', 12345, 'view')
        assert mark == 'doc_classified_ad_12345_view'

    def test_get_document_mark_custom_type(self):
        mark = DocumentTracker.get_document_mark('custom_type', 999, 'action')
        assert mark == 'doc_custom_type_999_action'

    def test_all_document_types_tracked(self, mock_analytics):
        doc_types = ['ad', 'user', 'media', 'message', 'review']

        for doc_type in doc_types:
            mock_analytics.reset_mock()
            DocumentTracker.mark_document_created(doc_type, 123, 'user1', {})
            assert mock_analytics.track_user_action.called

    def test_timestamp_included(self, mock_analytics):
        DocumentTracker.mark_document_created('ad', 12345, 'user123', {})

        call_args = mock_analytics.track_user_action.call_args
        properties = call_args[0][2]

        assert 'timestamp' in properties
        assert 'T' in properties['timestamp']  # ISO format check
        assert 'Z' not in properties['timestamp']  # utcnow() returns without Z

    def test_properties_preserved(self, mock_analytics):
        custom_props = {
            'category': 'vehicles',
            'price': 5000,
            'location': 'NYC',
        }
        DocumentTracker.mark_document_created('ad', 12345, 'user123', custom_props)

        call_args = mock_analytics.track_user_action.call_args
        properties = call_args[0][2]

        assert properties['category'] == 'vehicles'
        assert properties['price'] == 5000
        assert properties['location'] == 'NYC'

    def test_no_properties_creates_empty_dict(self, mock_analytics):
        DocumentTracker.mark_document_created('ad', 12345, 'user123', None)

        call_args = mock_analytics.track_user_action.call_args
        properties = call_args[0][2]

        # Should have at least the tracking metadata
        assert 'document_type' in properties
        assert 'document_id' in properties
        assert 'action' in properties
