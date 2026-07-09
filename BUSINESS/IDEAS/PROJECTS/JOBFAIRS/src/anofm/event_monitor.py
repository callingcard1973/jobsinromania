"""
ANOFM Event Monitor

Monitors, prioritizes, and stores job fair events from ANOFM website.
Implements intelligent prioritization based on region importance, timing,
and layoff indicators.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from config import get_config
from src.database.connection import get_db_session
from src.database.models import ANOFMEvent, EventStatus
from .website_scraper import ANOFMWebsiteScraper


class ANOFMEventMonitor:
    """
    ANOFM event monitoring and prioritization system.

    Features:
    - Automated event discovery via web scraping
    - Intelligent prioritization based on region and timing
    - Duplicate detection and event updates
    - Integration with layoff news monitoring
    - Database storage with status tracking
    """

    # Region priority scores based on layoff severity
    REGION_PRIORITIES = {
        'Hunedoara': 10,   # Steel industry layoffs - highest priority
        'Gorj': 8,         # Mining industry decline - high priority
        'Vaslui': 6,       # Textile industry closures - medium priority
        'Dolj': 4,         # Regional industrial decline
        'Caraș-Severin': 4,  # Mining related layoffs
        'Mehedinți': 3,    # Energy sector changes
    }

    # Timing-based scoring
    TIMING_SCORES = {
        (30, 90): 10,    # 30-90 days: optimal preparation time
        (14, 30): 8,     # 14-30 days: good preparation time
        (7, 14): 5,      # 7-14 days: short preparation time
        (3, 7): 3,       # 3-7 days: very short preparation time
        (0, 3): 1,       # 0-3 days: emergency participation only
    }

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the event monitor with configuration."""
        self.config = config or get_config()
        self.logger = logging.getLogger(__name__)
        self.scraper = ANOFMWebsiteScraper(config)

    def discover_events(self, max_pages: int = 5, store_events: bool = True) -> List[Dict]:
        """
        Discover new job fair events from ANOFM website.

        Args:
            max_pages: Maximum pages to scrape
            store_events: Whether to automatically store events in database

        Returns:
            List of discovered events with priority scores
        """
        self.logger.info("Starting event discovery from ANOFM website")

        # Scrape events from website
        raw_events = self.scraper.scrape_events(max_pages)
        self.logger.info(f"Scraped {len(raw_events)} raw events")

        # Filter for target regions
        target_events = self._filter_target_regions(raw_events)
        self.logger.info(f"Found {len(target_events)} events in target regions")

        # Calculate priority scores
        prioritized_events = []
        for event_data in target_events:
            try:
                priority_score = self._calculate_priority_score(event_data)
                event_data['priority_score'] = priority_score
                event_data['priority_breakdown'] = self._get_priority_breakdown(event_data)
                prioritized_events.append(event_data)
            except Exception as e:
                self.logger.warning(f"Failed to calculate priority for event: {e}")
                continue

        # Sort by priority score (highest first)
        prioritized_events.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        # Store events in database if requested
        if store_events:
            stored_count = self._store_events(prioritized_events)
            self.logger.info(f"Stored {stored_count} new events in database")

        self.logger.info(f"Event discovery complete: {len(prioritized_events)} prioritized events")
        return prioritized_events

    def _filter_target_regions(self, events: List[Dict]) -> List[Dict]:
        """Filter events to only include target regions."""
        target_regions = self.config.anofm.target_regions
        filtered_events = []

        for event in events:
            region = event.get('region')
            if region and region in target_regions:
                filtered_events.append(event)
            elif region and any(target in region for target in target_regions):
                # Handle partial matches (e.g., "Județul Hunedoara")
                filtered_events.append(event)
            elif not region:
                # If no region detected, check location for target regions
                location = event.get('location', '')
                if any(target.lower() in location.lower() for target in target_regions):
                    # Set region based on location match
                    for target in target_regions:
                        if target.lower() in location.lower():
                            event['region'] = target
                            filtered_events.append(event)
                            break

        return filtered_events

    def _calculate_priority_score(self, event_data: Dict) -> float:
        """
        Calculate priority score for an event based on multiple factors.

        Scoring factors:
        - Region importance (0-10 points)
        - Timing optimization (0-10 points)
        - Layoff indicators (0-5 points)
        - Event quality factors (0-5 points)
        """
        score = 0.0

        # Region-based scoring
        region = event_data.get('region', '')
        region_score = self.REGION_PRIORITIES.get(region, 1)  # Default 1 for other regions
        score += region_score

        # Timing-based scoring
        event_date = event_data.get('date')
        if event_date:
            days_ahead = (event_date - date.today()).days
            timing_score = self._get_timing_score(days_ahead)
            score += timing_score
        else:
            score += 1  # Default low score for events without dates

        # Layoff indicators (future enhancement)
        layoff_score = self._get_layoff_indicator_score(event_data)
        score += layoff_score

        # Event quality factors
        quality_score = self._get_event_quality_score(event_data)
        score += quality_score

        return round(score, 2)

    def _get_timing_score(self, days_ahead: int) -> float:
        """Get timing score based on days until event."""
        if days_ahead < 0:
            return 0  # Past events get 0 score

        for (min_days, max_days), score in self.TIMING_SCORES.items():
            if min_days <= days_ahead <= max_days:
                return score

        # Events more than 90 days ahead get reduced score
        if days_ahead > 90:
            return max(1, 10 - (days_ahead - 90) * 0.1)

        return 1  # Default score

    def _get_layoff_indicator_score(self, event_data: Dict) -> float:
        """
        Get additional score based on layoff indicators in the region.

        This would be enhanced with news monitoring in future versions.
        For now, it provides baseline scoring.
        """
        region = event_data.get('region', '')

        # Baseline layoff indicators by region
        layoff_indicators = {
            'Hunedoara': 3,  # Known steel industry layoffs
            'Gorj': 2,       # Mining industry decline
            'Vaslui': 2,     # Textile industry issues
        }

        return layoff_indicators.get(region, 0)

    def _get_event_quality_score(self, event_data: Dict) -> float:
        """Calculate event quality score based on available information."""
        score = 0

        # Complete contact information
        if event_data.get('organizer_email'):
            score += 1
        if event_data.get('organizer_phone'):
            score += 1

        # Clear registration deadline
        if event_data.get('registration_deadline'):
            score += 1

        # Detailed location information
        if event_data.get('location') and len(event_data['location']) > 10:
            score += 1

        # Professional event name
        name = event_data.get('name', '')
        if any(keyword in name.lower() for keyword in ['internațional', 'european', 'profesional', 'carieră']):
            score += 1

        return score

    def _get_priority_breakdown(self, event_data: Dict) -> Dict:
        """Get detailed breakdown of priority score calculation."""
        region = event_data.get('region', '')
        region_score = self.REGION_PRIORITIES.get(region, 1)

        days_ahead = 0
        timing_score = 0
        if event_data.get('date'):
            days_ahead = (event_data['date'] - date.today()).days
            timing_score = self._get_timing_score(days_ahead)

        layoff_score = self._get_layoff_indicator_score(event_data)
        quality_score = self._get_event_quality_score(event_data)

        return {
            'region_score': region_score,
            'timing_score': timing_score,
            'layoff_score': layoff_score,
            'quality_score': quality_score,
            'total_score': region_score + timing_score + layoff_score + quality_score,
            'days_ahead': days_ahead,
            'region': region
        }

    def _store_events(self, events: List[Dict]) -> int:
        """Store prioritized events in the database."""
        stored_count = 0

        with get_db_session() as session:
            for event_data in events:
                try:
                    # Check for existing event (avoid duplicates)
                    existing = self._find_existing_event(session, event_data)

                    if existing:
                        # Update existing event with new information
                        self._update_existing_event(session, existing, event_data)
                        self.logger.debug(f"Updated existing event: {existing.id}")
                    else:
                        # Create new event
                        new_event = self._create_new_event(session, event_data)
                        stored_count += 1
                        self.logger.debug(f"Created new event: {new_event.id}")

                    session.commit()

                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Failed to store event {event_data.get('name', 'Unknown')}: {e}")
                    continue

        return stored_count

    def _find_existing_event(self, session: Session, event_data: Dict) -> Optional[ANOFMEvent]:
        """Find existing event in database using fuzzy matching."""
        name = event_data.get('name', '').strip()
        event_date = event_data.get('date')
        region = event_data.get('region', '').strip()

        if not name or not event_date:
            return None

        # Try exact match first
        exact_match = session.query(ANOFMEvent).filter(
            ANOFMEvent.name == name,
            ANOFMEvent.date == event_date,
            ANOFMEvent.region == region
        ).first()

        if exact_match:
            return exact_match

        # Try fuzzy matching (same date and region, similar name)
        similar_events = session.query(ANOFMEvent).filter(
            ANOFMEvent.date == event_date,
            ANOFMEvent.region == region
        ).all()

        for event in similar_events:
            if self._names_are_similar(name, event.name):
                return event

        return None

    def _names_are_similar(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Check if two event names are similar (simple string similarity)."""
        # Simple similarity check - could be enhanced with fuzzy string matching
        name1_words = set(name1.lower().split())
        name2_words = set(name2.lower().split())

        if not name1_words or not name2_words:
            return False

        intersection = len(name1_words.intersection(name2_words))
        union = len(name1_words.union(name2_words))

        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold

    def _update_existing_event(self, session: Session, event: ANOFMEvent, new_data: Dict):
        """Update existing event with new information."""
        # Update fields that might have changed
        if new_data.get('organizer_email') and not event.organizer_email:
            event.organizer_email = new_data['organizer_email']

        if new_data.get('organizer_phone') and not event.organizer_phone:
            event.organizer_phone = new_data['organizer_phone']

        if new_data.get('organizer_contact') and not event.organizer_contact:
            event.organizer_contact = new_data['organizer_contact']

        if new_data.get('registration_deadline') and not event.registration_deadline:
            event.registration_deadline = new_data['registration_deadline']

        if new_data.get('anofm_url') and not event.anofm_url:
            event.anofm_url = new_data['anofm_url']

        # Always update last_scraped
        event.last_scraped = datetime.now()

        # Update notes with priority information
        priority_breakdown = new_data.get('priority_breakdown', {})
        priority_note = f"Priority Score: {new_data.get('priority_score', 0)} " \
                       f"(Region: {priority_breakdown.get('region_score', 0)}, " \
                       f"Timing: {priority_breakdown.get('timing_score', 0)}, " \
                       f"Quality: {priority_breakdown.get('quality_score', 0)})"

        if event.notes:
            event.notes = f"{event.notes}\n\nUpdated {datetime.now().strftime('%Y-%m-%d')}: {priority_note}"
        else:
            event.notes = priority_note

    def _create_new_event(self, session: Session, event_data: Dict) -> ANOFMEvent:
        """Create a new ANOFM event from scraped data."""
        priority_breakdown = event_data.get('priority_breakdown', {})
        priority_note = f"Priority Score: {event_data.get('priority_score', 0)} " \
                       f"(Region: {priority_breakdown.get('region_score', 0)}, " \
                       f"Timing: {priority_breakdown.get('timing_score', 0)}, " \
                       f"Quality: {priority_breakdown.get('quality_score', 0)})"

        event = ANOFMEvent(
            name=event_data.get('name', ''),
            date=event_data.get('date'),
            end_date=event_data.get('end_date'),
            location=event_data.get('location', ''),
            region=event_data.get('region', ''),
            organizer_contact=event_data.get('organizer_contact'),
            organizer_email=event_data.get('organizer_email'),
            organizer_phone=event_data.get('organizer_phone'),
            registration_deadline=event_data.get('registration_deadline'),
            anofm_url=event_data.get('anofm_url'),
            last_scraped=datetime.now(),
            status=EventStatus.ANNOUNCED,
            notes=priority_note,
            currency='RON'  # Default currency for Romanian events
        )

        session.add(event)
        session.flush()  # Get the ID
        return event

    def get_upcoming_events(self,
                          limit: int = 20,
                          days_ahead: int = 90,
                          min_priority: float = 5.0) -> List[Dict]:
        """
        Get upcoming prioritized events from database.

        Args:
            limit: Maximum number of events to return
            days_ahead: Only include events within this many days
            min_priority: Minimum priority score filter

        Returns:
            List of upcoming events with priority information
        """
        max_date = date.today() + timedelta(days=days_ahead)

        with get_db_session() as session:
            events = session.query(ANOFMEvent).filter(
                ANOFMEvent.date >= date.today(),
                ANOFMEvent.date <= max_date,
                ANOFMEvent.status.in_([EventStatus.ANNOUNCED, EventStatus.REGISTERED])
            ).order_by(ANOFMEvent.date.asc()).limit(limit).all()

            # Convert to dict format with priority information
            event_list = []
            for event in events:
                event_dict = {
                    'id': event.id,
                    'name': event.name,
                    'date': event.date,
                    'end_date': event.end_date,
                    'location': event.location,
                    'region': event.region,
                    'organizer_email': event.organizer_email,
                    'organizer_phone': event.organizer_phone,
                    'organizer_contact': event.organizer_contact,
                    'registration_deadline': event.registration_deadline,
                    'anofm_url': event.anofm_url,
                    'status': event.status.value,
                    'notes': event.notes,
                    'created_at': event.created_at,
                    'last_scraped': event.last_scraped
                }

                # Recalculate current priority score
                try:
                    current_priority = self._calculate_priority_score(event_dict)
                    if current_priority >= min_priority:
                        event_dict['priority_score'] = current_priority
                        event_dict['priority_breakdown'] = self._get_priority_breakdown(event_dict)
                        event_list.append(event_dict)
                except Exception as e:
                    self.logger.warning(f"Failed to calculate priority for event {event.id}: {e}")

        # Sort by priority score
        event_list.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        return event_list

    def monitor_events_continuous(self,
                                check_interval_hours: Optional[int] = None) -> Dict:
        """
        Run continuous monitoring (single check) - meant to be called by scheduler.

        Args:
            check_interval_hours: Override default check interval

        Returns:
            Summary of monitoring results
        """
        interval = check_interval_hours or self.config.anofm.check_interval_hours

        self.logger.info(f"Starting ANOFM event monitoring check")

        try:
            # Discover new events
            new_events = self.discover_events()

            # Get current high-priority events
            upcoming_events = self.get_upcoming_events(limit=10, min_priority=8.0)

            # Generate summary
            summary = {
                'timestamp': datetime.now(),
                'new_events_discovered': len(new_events),
                'high_priority_upcoming': len(upcoming_events),
                'check_interval_hours': interval,
                'target_regions': self.config.anofm.target_regions,
                'success': True
            }

            # Log high-priority events
            if upcoming_events:
                self.logger.info("High-priority upcoming events:")
                for event in upcoming_events[:5]:  # Log top 5
                    self.logger.info(
                        f"  {event['name']} - {event['date']} - "
                        f"{event['region']} (Priority: {event.get('priority_score', 0)})"
                    )

            self.logger.info(f"ANOFM monitoring check complete: {summary}")
            return summary

        except Exception as e:
            error_summary = {
                'timestamp': datetime.now(),
                'error': str(e),
                'success': False
            }
            self.logger.error(f"ANOFM monitoring failed: {e}")
            return error_summary

    def get_monitoring_statistics(self) -> Dict:
        """Get statistics about monitored events."""
        with get_db_session() as session:
            # Total events by region
            region_stats = {}
            for region in self.config.anofm.target_regions:
                count = session.query(ANOFMEvent).filter(
                    ANOFMEvent.region == region
                ).count()
                region_stats[region] = count

            # Events by status
            status_stats = {}
            for status in EventStatus:
                count = session.query(ANOFMEvent).filter(
                    ANOFMEvent.status == status
                ).count()
                status_stats[status.value] = count

            # Upcoming events count
            upcoming_count = session.query(ANOFMEvent).filter(
                ANOFMEvent.date >= date.today(),
                ANOFMEvent.status.in_([EventStatus.ANNOUNCED, EventStatus.REGISTERED])
            ).count()

            # Recent discoveries (last 7 days)
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_count = session.query(ANOFMEvent).filter(
                ANOFMEvent.created_at >= recent_cutoff
            ).count()

            return {
                'total_events': sum(region_stats.values()),
                'events_by_region': region_stats,
                'events_by_status': status_stats,
                'upcoming_events': upcoming_count,
                'recent_discoveries': recent_count,
                'target_regions': self.config.anofm.target_regions,
                'timestamp': datetime.now()
            }