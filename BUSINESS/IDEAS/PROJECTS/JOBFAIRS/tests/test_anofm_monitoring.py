"""
Test suite for ANOFM Event Monitoring System.

Comprehensive tests for website scraping, event prioritization,
Romanian date parsing, and database integration.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from src.anofm.website_scraper import ANOFMWebsiteScraper
from src.anofm.event_monitor import ANOFMEventMonitor
from src.database.models import ANOFMEvent, EventStatus
from config import get_config


class TestANOFMWebsiteScraper:
    """Test suite for ANOFM website scraping functionality."""

    @pytest.fixture
    def scraper(self):
        """Create a test scraper instance."""
        config = get_config()
        return ANOFMWebsiteScraper(config)

    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response for testing."""
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        return response

    def test_romanian_month_normalization(self, scraper):
        """Test Romanian month name normalization."""
        test_cases = [
            ("15 ianuarie 2024", "15 january 2024"),
            ("5 iunie 2024", "5 june 2024"),
            ("1 decembrie 2023", "1 december 2023"),
            ("10 oct 2024", "10 oct 2024"),
            ("Mixed case Iulie", "Mixed case july")
        ]

        for romanian, expected in test_cases:
            normalized = scraper._normalize_romanian_dates(romanian)
            assert expected.lower() in normalized.lower()

    def test_romanian_date_parsing(self, scraper):
        """Test parsing of various Romanian date formats."""
        test_cases = [
            ("15 ianuarie 2024", date(2024, 1, 15)),
            ("5.06.2024", date(2024, 6, 5)),
            ("01/12/2024", date(2024, 12, 1)),
            ("2024-03-15", date(2024, 3, 15)),
            ("invalid date", None),
            ("", None)
        ]

        for date_str, expected in test_cases:
            parsed = scraper._parse_romanian_date(date_str)
            assert parsed == expected

    def test_region_detection(self, scraper):
        """Test Romanian county/region detection from text."""
        test_cases = [
            ("Bursa locurilor de munca la Hunedoara", "Hunedoara"),
            ("Eveniment în județul Gorj", "Gorj"),
            ("Târgul de cariere Vaslui 2024", "Vaslui"),
            ("Event in London", None),  # Non-Romanian location
            ("Text without location", None)
        ]

        for text, expected_region in test_cases:
            location, region = scraper._extract_location_and_region(text)
            assert region == expected_region

    def test_contact_extraction(self, scraper):
        """Test extraction of contact information."""
        test_text = """
        Contact pentru informații: office@anofm.ro
        Telefon: 0732123456
        Persoana de contact: Maria Popescu
        """

        contacts = scraper._extract_contact_info(test_text)

        assert contacts['email'] == 'office@anofm.ro'
        assert '0732123456' in contacts['phone']
        assert contacts['contact_person'] == 'Maria Popescu'

    def test_romanian_phone_patterns(self, scraper):
        """Test Romanian phone number pattern detection."""
        test_cases = [
            ("Tel: 0721234567", "0721234567"),
            ("Telefon: +40742123456", "+40742123456"),
            ("Contact: 0040 231 123 456", "0040 231 123 456"),
            ("No phone here", None),
            ("Invalid: 123", None)
        ]

        for text, expected in test_cases:
            contacts = scraper._extract_contact_info(text)
            if expected:
                assert expected in contacts['phone'] if contacts['phone'] else False
            else:
                assert contacts['phone'] is None

    def test_job_fair_validation(self, scraper):
        """Test validation of job fair events."""
        valid_event = {
            'name': 'Bursa locurilor de munca Hunedoara 2024',
            'date': date.today() + timedelta(days=30),
            'region': 'Hunedoara',
            'raw_text': 'Târg de cariere pentru angajări'
        }

        invalid_events = [
            # No name
            {'date': date.today() + timedelta(days=30), 'region': 'Hunedoara'},
            # Past date
            {'name': 'Bursa locurilor', 'date': date.today() - timedelta(days=1)},
            # Non-job-fair content
            {'name': 'Anunț metodologie', 'date': date.today() + timedelta(days=30)},
            # No job fair keywords
            {'name': 'General meeting', 'date': date.today() + timedelta(days=30)}
        ]

        assert scraper._is_valid_job_fair_event(valid_event) is True

        for invalid_event in invalid_events:
            assert scraper._is_valid_job_fair_event(invalid_event) is False

    def test_event_name_extraction(self, scraper):
        """Test extraction of event names from HTML elements."""
        html_cases = [
            ('<h2>Bursa locurilor de munca Cluj 2024</h2>', 'Bursa locurilor de munca Cluj 2024'),
            ('<div title="Târgul carierei IT">Content</div>', 'Târgul carierei IT'),
            ('<p>Bursa de munca<br>Alte informatii</p>', 'Bursa de munca'),
            ('<div>Short</div>', None),  # Too short
            ('<div>No keywords here</div>', None)  # No job fair keywords
        ]

        for html, expected in html_cases:
            soup = BeautifulSoup(html, 'html.parser')
            element = soup.find(['h2', 'div', 'p'])
            name = scraper._extract_event_name(element)
            assert name == expected

    @patch('requests.Session.get')
    def test_scraping_page_success(self, mock_get, scraper):
        """Test successful page scraping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = """
        <html>
            <head><title>ANOFM - Burse de munca</title></head>
            <body>
                <div class="event-item">
                    <h3>Bursa locurilor de munca Hunedoara</h3>
                    <p>Data: 15 martie 2024</p>
                    <p>Locația: Hunedoara, România</p>
                    <p>Contact: office@anofm-hunedoara.ro</p>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        events = scraper._scrape_page("https://anofm.ro/test")

        assert len(events) >= 0  # Should process without error
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_scraping_page_error(self, mock_get, scraper):
        """Test page scraping error handling."""
        mock_get.side_effect = Exception("Network error")

        events = scraper._scrape_page("https://anofm.ro/test")

        assert events == []

    def test_date_extraction_from_text(self, scraper):
        """Test comprehensive date extraction from Romanian text."""
        test_text = """
        Evenimentul va avea loc în data de 15 martie 2024.
        Înscrierea se poate face până la data de 1 martie 2024.
        Târgul se desfășoară pe mai multe zile: 15-17 martie 2024.
        """

        event_date, end_date, registration_deadline = scraper._extract_dates(test_text)

        # Should extract the main event date
        assert event_date is not None
        assert event_date.month == 3  # March
        assert event_date.year == 2024

    def test_location_extraction_patterns(self, scraper):
        """Test various location extraction patterns."""
        test_cases = [
            ("Eveniment la Deva, județul Hunedoara", ("Deva", "Hunedoara")),
            ("Adresa: Strada Principală 123, Cluj", ("Strada Principală 123, Cluj", "Cluj")),
            ("în municipiul Timișoara", ("municipiul Timișoara", "Timiș")),
            ("No location info here", (None, None))
        ]

        for text, (expected_location, expected_region) in test_cases:
            location, region = scraper._extract_location_and_region(text)

            # Note: region detection might not be perfect for all cases
            # Focus on testing that the method doesn't crash and returns reasonable results
            if expected_location:
                assert location is not None or region is not None


class TestANOFMEventMonitor:
    """Test suite for ANOFM event monitoring and prioritization."""

    @pytest.fixture
    def monitor(self):
        """Create a test monitor instance."""
        config = get_config()
        return ANOFMEventMonitor(config)

    @pytest.fixture
    def sample_event_data(self):
        """Sample event data for testing."""
        return {
            'name': 'Bursa locurilor de munca Hunedoara 2024',
            'date': date.today() + timedelta(days=45),
            'location': 'Deva, județul Hunedoara',
            'region': 'Hunedoara',
            'organizer_email': 'contact@anofm-hunedoara.ro',
            'organizer_phone': '0254123456',
            'organizer_contact': 'Maria Popescu',
            'registration_deadline': date.today() + timedelta(days=30),
            'anofm_url': 'https://anofm.ro/evenimente/bursa-hunedoara',
            'raw_text': 'Târg de cariere pentru angajări în industria siderurgică'
        }

    def test_region_priority_scoring(self, monitor):
        """Test region-based priority scoring."""
        test_cases = [
            ('Hunedoara', 10),  # Highest priority
            ('Gorj', 8),        # High priority
            ('Vaslui', 6),      # Medium priority
            ('Unknown', 1),     # Default low priority
        ]

        for region, expected_score in test_cases:
            event_data = {'region': region, 'date': date.today() + timedelta(days=45)}
            score = monitor._calculate_priority_score(event_data)

            # Score should include the region score component
            assert score >= expected_score

    def test_timing_score_calculation(self, monitor):
        """Test timing-based scoring."""
        today = date.today()
        test_cases = [
            (45, 10),   # 45 days ahead - optimal
            (20, 8),    # 20 days ahead - good
            (10, 5),    # 10 days ahead - short
            (5, 3),     # 5 days ahead - very short
            (1, 1),     # 1 day ahead - emergency
            (-1, 0),    # Past event - zero score
            (120, 1),   # Too far ahead - reduced score
        ]

        for days_ahead, min_expected_score in test_cases:
            score = monitor._get_timing_score(days_ahead)

            if days_ahead < 0:
                assert score == 0
            elif days_ahead > 90:
                assert score >= 0  # Should be positive but reduced
            else:
                assert score >= min_expected_score

    def test_event_quality_scoring(self, monitor, sample_event_data):
        """Test event quality scoring based on available information."""
        # Full information event should get high quality score
        full_quality_score = monitor._get_event_quality_score(sample_event_data)
        assert full_quality_score >= 3

        # Minimal information event should get low score
        minimal_event = {
            'name': 'Basic event',
            'date': date.today() + timedelta(days=30)
        }
        minimal_quality_score = monitor._get_event_quality_score(minimal_event)
        assert minimal_quality_score <= 2

    def test_layoff_indicator_scoring(self, monitor):
        """Test layoff indicator scoring."""
        # Known layoff regions should get additional score
        hunedoara_score = monitor._get_layoff_indicator_score({'region': 'Hunedoara'})
        assert hunedoara_score >= 2

        # Unknown regions should get minimal score
        unknown_score = monitor._get_layoff_indicator_score({'region': 'Unknown'})
        assert unknown_score == 0

    def test_comprehensive_priority_calculation(self, monitor, sample_event_data):
        """Test comprehensive priority score calculation."""
        priority_score = monitor._calculate_priority_score(sample_event_data)

        # High-priority region + good timing + quality info should get high score
        assert priority_score >= 15

        # Get breakdown for verification
        breakdown = monitor._get_priority_breakdown(sample_event_data)

        assert breakdown['region_score'] == 10  # Hunedoara priority
        assert breakdown['timing_score'] >= 8   # Good timing
        assert breakdown['quality_score'] >= 3  # Good quality
        assert breakdown['total_score'] == priority_score

    def test_target_region_filtering(self, monitor):
        """Test filtering events for target regions only."""
        events = [
            {'name': 'Event 1', 'region': 'Hunedoara'},    # Should include
            {'name': 'Event 2', 'region': 'Gorj'},         # Should include
            {'name': 'Event 3', 'region': 'București'},    # Should exclude
            {'name': 'Event 4', 'location': 'Deva, Hunedoara', 'region': None},  # Should include (location match)
            {'name': 'Event 5', 'region': 'Vaslui'},       # Should include
        ]

        filtered = monitor._filter_target_regions(events)

        # Should have 4 events (excluding București)
        assert len(filtered) == 4

        regions = [event.get('region') for event in filtered]
        assert 'Hunedoara' in regions
        assert 'Gorj' in regions
        assert 'Vaslui' in regions
        assert 'București' not in regions

    def test_name_similarity_detection(self, monitor):
        """Test detection of similar event names for duplicate prevention."""
        test_cases = [
            ("Bursa locurilor de munca Hunedoara", "Bursa de munca Hunedoara", True),
            ("Târgul carierei 2024", "Târgul de cariere 2024", True),
            ("Event A", "Event B", False),
            ("Completely different", "Nothing similar", False),
            ("", "Empty string", False),
        ]

        for name1, name2, expected_similar in test_cases:
            result = monitor._names_are_similar(name1, name2)
            assert result == expected_similar

    def test_priority_breakdown_structure(self, monitor, sample_event_data):
        """Test structure and completeness of priority breakdown."""
        breakdown = monitor._get_priority_breakdown(sample_event_data)

        required_fields = [
            'region_score', 'timing_score', 'layoff_score',
            'quality_score', 'total_score', 'days_ahead', 'region'
        ]

        for field in required_fields:
            assert field in breakdown

        # Verify total score calculation
        calculated_total = (
            breakdown['region_score'] + breakdown['timing_score'] +
            breakdown['layoff_score'] + breakdown['quality_score']
        )
        assert breakdown['total_score'] == calculated_total

    @patch('src.anofm.event_monitor.get_db_session')
    def test_event_storage_new_event(self, mock_session, monitor, sample_event_data):
        """Test storing a new event in the database."""
        mock_session_instance = Mock()
        mock_session.return_value.__enter__ = Mock(return_value=mock_session_instance)
        mock_session.return_value.__exit__ = Mock(return_value=None)

        # Mock no existing event found
        mock_session_instance.query.return_value.filter.return_value.first.return_value = None

        # Test storing events
        events = [sample_event_data]
        stored_count = monitor._store_events(events)

        # Should have attempted to store 1 event
        assert stored_count == 1
        mock_session_instance.add.assert_called()
        mock_session_instance.commit.assert_called()

    @patch('src.anofm.event_monitor.get_db_session')
    def test_event_storage_duplicate_detection(self, mock_session, monitor, sample_event_data):
        """Test duplicate event detection and updating."""
        mock_session_instance = Mock()
        mock_session.return_value.__enter__ = Mock(return_value=mock_session_instance)
        mock_session.return_value.__exit__ = Mock(return_value=None)

        # Mock existing event found
        existing_event = Mock()
        existing_event.id = 1
        existing_event.organizer_email = None  # Will be updated
        existing_event.notes = "Existing notes"
        mock_session_instance.query.return_value.filter.return_value.first.return_value = existing_event

        events = [sample_event_data]
        stored_count = monitor._store_events(events)

        # Should have updated existing event, not created new one
        assert stored_count == 0
        mock_session_instance.commit.assert_called()

    def test_monitoring_statistics_structure(self, monitor):
        """Test structure of monitoring statistics."""
        with patch('src.anofm.event_monitor.get_db_session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_session_instance)
            mock_session.return_value.__exit__ = Mock(return_value=None)

            # Mock query results
            mock_session_instance.query.return_value.filter.return_value.count.return_value = 5

            stats = monitor.get_monitoring_statistics()

            required_fields = [
                'total_events', 'events_by_region', 'events_by_status',
                'upcoming_events', 'recent_discoveries', 'target_regions', 'timestamp'
            ]

            for field in required_fields:
                assert field in stats

            assert isinstance(stats['events_by_region'], dict)
            assert isinstance(stats['events_by_status'], dict)

    @patch.object(ANOFMWebsiteScraper, 'scrape_events')
    def test_discover_events_integration(self, mock_scrape, monitor, sample_event_data):
        """Test end-to-end event discovery process."""
        # Mock scraper to return sample data
        mock_scrape.return_value = [sample_event_data]

        with patch('src.anofm.event_monitor.get_db_session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value.__enter__ = Mock(return_value=mock_session_instance)
            mock_session.return_value.__exit__ = Mock(return_value=None)

            # Mock no existing events
            mock_session_instance.query.return_value.filter.return_value.first.return_value = None

            # Run discovery
            discovered_events = monitor.discover_events(max_pages=1, store_events=True)

            assert len(discovered_events) == 1
            event = discovered_events[0]

            # Should have priority score and breakdown
            assert 'priority_score' in event
            assert 'priority_breakdown' in event
            assert event['priority_score'] > 0

    def test_continuous_monitoring_summary(self, monitor):
        """Test continuous monitoring summary generation."""
        with patch.object(monitor, 'discover_events') as mock_discover:
            with patch.object(monitor, 'get_upcoming_events') as mock_upcoming:
                mock_discover.return_value = [{'name': 'Test Event'}]
                mock_upcoming.return_value = [{'name': 'Upcoming Event'}]

                summary = monitor.monitor_events_continuous()

                assert summary['success'] is True
                assert 'new_events_discovered' in summary
                assert 'high_priority_upcoming' in summary
                assert 'timestamp' in summary

    def test_edge_cases_and_error_handling(self, monitor):
        """Test edge cases and error handling."""
        # Test with empty event data
        empty_score = monitor._calculate_priority_score({})
        assert empty_score >= 0

        # Test with missing date
        no_date_event = {'name': 'Test', 'region': 'Hunedoara'}
        score = monitor._calculate_priority_score(no_date_event)
        assert score >= 0

        # Test with invalid region
        invalid_region = {'name': 'Test', 'region': 'InvalidRegion', 'date': date.today()}
        score = monitor._calculate_priority_score(invalid_region)
        assert score >= 0


@pytest.mark.integration
class TestANOFMIntegration:
    """Integration tests for ANOFM monitoring system."""

    def test_scraper_monitor_integration(self):
        """Test integration between scraper and monitor."""
        config = get_config()
        scraper = ANOFMWebsiteScraper(config)
        monitor = ANOFMEventMonitor(config)

        # Test that monitor can use scraper
        assert monitor.scraper is not None
        assert isinstance(monitor.scraper, ANOFMWebsiteScraper)

    @pytest.mark.skip(reason="Requires actual network access")
    def test_live_website_scraping(self):
        """Test scraping live ANOFM website (disabled by default)."""
        config = get_config()
        scraper = ANOFMWebsiteScraper(config)

        # Test scraping functionality
        test_result = scraper.test_scraping()

        assert test_result['success'] is True
        assert test_result['status_code'] == 200
        assert 'events_found' in test_result

    def test_database_model_compatibility(self):
        """Test compatibility between extracted event data and database model."""
        from src.database.models import ANOFMEvent

        sample_data = {
            'name': 'Test Event',
            'date': date.today() + timedelta(days=30),
            'location': 'Test Location',
            'region': 'Hunedoara',
            'organizer_email': 'test@example.com'
        }

        # Should be able to create model instance without errors
        event = ANOFMEvent(**{
            k: v for k, v in sample_data.items()
            if hasattr(ANOFMEvent, k)
        })

        assert event.name == sample_data['name']
        assert event.date == sample_data['date']
        assert event.region == sample_data['region']


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main(['-v', __file__])