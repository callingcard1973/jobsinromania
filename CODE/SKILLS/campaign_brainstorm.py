#!/usr/bin/env python3
"""
Campaign Brainstorm Skill - Generate campaign ideas from data patterns
Based on superpowers brainstorming pattern

Analyzes scraped data to suggest:
- Target segments
- Campaign timing
- Message angles
- A/B test ideas

Usage:
    python3 campaign_brainstorm.py /path/to/contacts.csv
    python3 campaign_brainstorm.py /mnt/hdd/SCRAPER_DATA/ --all
    python3 campaign_brainstorm.py --country SPAIN --industry healthcare

Examples:
    # Brainstorm from a single CSV
    python3 campaign_brainstorm.py /mnt/hdd/SCRAPER_DATA/SPAIN_MASTER.csv

    # Brainstorm across all data
    python3 campaign_brainstorm.py /mnt/hdd/SCRAPER_DATA/ --all

    # Focus on specific segment
    python3 campaign_brainstorm.py data.csv --focus "IT managers"
"""

import sys
import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, field

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')


@dataclass
class Segment:
    """A contact segment for targeting."""
    name: str
    size: int
    characteristics: List[str]
    campaign_angle: str
    priority: int = 5  # 1-10


@dataclass
class CampaignIdea:
    """A campaign idea."""
    name: str
    target_segment: str
    message_angle: str
    timing: str
    expected_response: str
    ab_test_ideas: List[str]
    priority: int = 5


class CampaignBrainstormer:
    """Generate campaign ideas from data analysis."""

    def __init__(self):
        self.data: List[Dict] = []
        self.segments: List[Segment] = []
        self.ideas: List[CampaignIdea] = []

    def load_csv(self, path: Path) -> int:
        """Load data from CSV file."""
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.data.extend(rows)
                return len(rows)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return 0

    def load_directory(self, path: Path) -> int:
        """Load all CSVs from directory."""
        total = 0
        for csv_file in path.glob('**/*.csv'):
            if 'MASTER' in csv_file.name.upper():
                count = self.load_csv(csv_file)
                if count > 0:
                    print(f"  Loaded {count} records from {csv_file.name}")
                    total += count
        return total

    def analyze_data(self) -> Dict[str, Any]:
        """Analyze loaded data for patterns."""
        if not self.data:
            return {}

        analysis = {
            'total_records': len(self.data),
            'fields': list(self.data[0].keys()) if self.data else [],
            'patterns': {}
        }

        # Analyze each field
        field_stats = {}
        for field in analysis['fields']:
            values = [row.get(field, '') for row in self.data if row.get(field)]
            if values:
                counter = Counter(values)
                field_stats[field] = {
                    'unique': len(counter),
                    'top_5': counter.most_common(5),
                    'fill_rate': len(values) / len(self.data)
                }

        analysis['field_stats'] = field_stats

        # Find location patterns
        location_fields = ['location', 'city', 'country', 'region', 'area']
        for field in location_fields:
            if field in analysis['fields']:
                values = [row.get(field, '') for row in self.data if row.get(field)]
                if values:
                    analysis['patterns']['locations'] = Counter(values).most_common(10)
                    break

        # Find industry/sector patterns
        industry_fields = ['industry', 'sector', 'category', 'type']
        for field in industry_fields:
            if field in analysis['fields']:
                values = [row.get(field, '') for row in self.data if row.get(field)]
                if values:
                    analysis['patterns']['industries'] = Counter(values).most_common(10)
                    break

        # Find title/role patterns
        title_fields = ['title', 'job_title', 'position', 'role']
        for field in title_fields:
            if field in analysis['fields']:
                values = [row.get(field, '') for row in self.data if row.get(field)]
                if values:
                    # Extract common title keywords
                    keywords = []
                    for v in values:
                        words = re.findall(r'\b\w+\b', v.lower())
                        keywords.extend(words)
                    analysis['patterns']['title_keywords'] = Counter(keywords).most_common(20)
                    break

        # Find company size indicators
        size_fields = ['company_size', 'employees', 'size']
        for field in size_fields:
            if field in analysis['fields']:
                values = [row.get(field, '') for row in self.data if row.get(field)]
                if values:
                    analysis['patterns']['company_sizes'] = Counter(values).most_common(10)
                    break

        return analysis

    def identify_segments(self, analysis: Dict) -> List[Segment]:
        """Identify targetable segments from analysis."""
        segments = []

        # Location-based segments
        if 'locations' in analysis.get('patterns', {}):
            top_locations = analysis['patterns']['locations'][:5]
            for location, count in top_locations:
                if count >= 10:  # Minimum segment size
                    segments.append(Segment(
                        name=f"{location} professionals",
                        size=count,
                        characteristics=[f"Based in {location}"],
                        campaign_angle=f"Local job opportunities in {location}",
                        priority=7
                    ))

        # Industry-based segments
        if 'industries' in analysis.get('patterns', {}):
            top_industries = analysis['patterns']['industries'][:5]
            for industry, count in top_industries:
                if count >= 10:
                    segments.append(Segment(
                        name=f"{industry} sector",
                        size=count,
                        characteristics=[f"Works in {industry}"],
                        campaign_angle=f"Industry-specific opportunities in {industry}",
                        priority=8
                    ))

        # Title-based segments
        if 'title_keywords' in analysis.get('patterns', {}):
            # Look for seniority indicators
            keywords = dict(analysis['patterns']['title_keywords'])

            # Senior/Manager segment
            senior_keywords = ['senior', 'manager', 'director', 'head', 'lead', 'chief']
            senior_count = sum(keywords.get(k, 0) for k in senior_keywords)
            if senior_count >= 20:
                segments.append(Segment(
                    name="Senior professionals",
                    size=senior_count,
                    characteristics=["Senior/management level titles"],
                    campaign_angle="Leadership opportunities and career advancement",
                    priority=9
                ))

            # Technical segment
            tech_keywords = ['developer', 'engineer', 'programmer', 'technical', 'software', 'it']
            tech_count = sum(keywords.get(k, 0) for k in tech_keywords)
            if tech_count >= 20:
                segments.append(Segment(
                    name="Technical professionals",
                    size=tech_count,
                    characteristics=["Technical/engineering roles"],
                    campaign_angle="Tech opportunities and skill-based matching",
                    priority=8
                ))

            # Healthcare segment
            health_keywords = ['nurse', 'doctor', 'medical', 'healthcare', 'care', 'health']
            health_count = sum(keywords.get(k, 0) for k in health_keywords)
            if health_count >= 20:
                segments.append(Segment(
                    name="Healthcare workers",
                    size=health_count,
                    characteristics=["Healthcare/medical roles"],
                    campaign_angle="Healthcare opportunities across Europe",
                    priority=9
                ))

        self.segments = segments
        return segments

    def generate_ideas(self, segments: List[Segment]) -> List[CampaignIdea]:
        """Generate campaign ideas for segments."""
        ideas = []

        for segment in segments:
            # Generate campaign idea based on segment
            idea = CampaignIdea(
                name=f"{segment.name} Outreach",
                target_segment=segment.name,
                message_angle=segment.campaign_angle,
                timing=self._suggest_timing(segment),
                expected_response=self._estimate_response(segment),
                ab_test_ideas=self._generate_ab_tests(segment),
                priority=segment.priority
            )
            ideas.append(idea)

        # Add cross-segment ideas
        if len(segments) >= 2:
            ideas.append(CampaignIdea(
                name="Multi-segment nurture campaign",
                target_segment="All segments",
                message_angle="Personalized by segment with shared value proposition",
                timing="Staggered: 1 segment per week",
                expected_response="Varies by segment, expect 15-25% total open rate",
                ab_test_ideas=[
                    "Test segment-specific vs. generic subject lines",
                    "Test sending day across segments",
                    "Test single CTA vs. multiple options"
                ],
                priority=7
            ))

        self.ideas = sorted(ideas, key=lambda x: -x.priority)
        return self.ideas

    def _suggest_timing(self, segment: Segment) -> str:
        """Suggest campaign timing based on segment."""
        if 'healthcare' in segment.name.lower():
            return "Tuesday-Thursday, avoid weekends (shift workers check email during breaks)"
        elif 'senior' in segment.name.lower() or 'manager' in segment.name.lower():
            return "Tuesday-Wednesday 9-11 AM (executives check email early)"
        elif 'technical' in segment.name.lower():
            return "Tuesday-Thursday 10 AM-2 PM (developers check email late morning)"
        else:
            return "Tuesday-Thursday 10 AM (general best practice)"

    def _estimate_response(self, segment: Segment) -> str:
        """Estimate expected response rate."""
        if segment.priority >= 8:
            return "Expect 20-30% open rate, 3-5% click rate (high-value segment)"
        elif segment.priority >= 6:
            return "Expect 15-20% open rate, 2-3% click rate (good segment)"
        else:
            return "Expect 10-15% open rate, 1-2% click rate (standard)"

    def _generate_ab_tests(self, segment: Segment) -> List[str]:
        """Generate A/B test ideas for segment."""
        tests = [
            f"Subject line: Mention {segment.name} vs. generic greeting",
            "CTA: 'Apply Now' vs. 'Learn More'",
            "Sender name: Personal name vs. Company name"
        ]

        if 'senior' in segment.name.lower():
            tests.append("Tone: Formal vs. conversational")
        if 'technical' in segment.name.lower():
            tests.append("Content: Salary range vs. tech stack focus")
        if 'healthcare' in segment.name.lower():
            tests.append("Focus: Work-life balance vs. career growth")

        return tests[:4]

    def brainstorm(self, path: Path, all_files: bool = False) -> Dict[str, Any]:
        """Run full brainstorming session."""
        print(f"\n{'='*70}")
        print(f"CAMPAIGN BRAINSTORM")
        print(f"{'='*70}")

        # Load data
        if path.is_file():
            count = self.load_csv(path)
            print(f"Loaded {count} records from {path.name}")
        elif all_files:
            count = self.load_directory(path)
            print(f"Loaded {count} total records")
        else:
            # Look for MASTER files only
            count = 0
            for csv_file in path.glob('*MASTER*.csv'):
                c = self.load_csv(csv_file)
                if c > 0:
                    print(f"  Loaded {c} from {csv_file.name}")
                    count += c

        if not self.data:
            print("No data loaded!")
            return {'error': 'No data loaded'}

        # Analyze
        print(f"\n[1/3] Analyzing data patterns...")
        analysis = self.analyze_data()

        print(f"  Fields: {len(analysis.get('fields', []))}")
        print(f"  Records: {analysis.get('total_records', 0)}")

        if analysis.get('patterns'):
            for pattern_type, values in analysis['patterns'].items():
                if values:
                    print(f"  {pattern_type}: {len(values)} unique values")

        # Identify segments
        print(f"\n[2/3] Identifying segments...")
        segments = self.identify_segments(analysis)
        print(f"  Found {len(segments)} targetable segments:")
        for seg in segments:
            print(f"    - {seg.name} ({seg.size} contacts)")

        # Generate ideas
        print(f"\n[3/3] Generating campaign ideas...")
        ideas = self.generate_ideas(segments)

        # Print ideas
        print(f"\n{'='*70}")
        print("CAMPAIGN IDEAS")
        print(f"{'='*70}")

        for i, idea in enumerate(ideas, 1):
            print(f"\n{i}. {idea.name}")
            print(f"   Target: {idea.target_segment}")
            print(f"   Angle: {idea.message_angle}")
            print(f"   Timing: {idea.timing}")
            print(f"   Expected: {idea.expected_response}")
            print(f"   A/B Tests:")
            for test in idea.ab_test_ideas:
                print(f"     - {test}")

        # Summary
        print(f"\n{'='*70}")
        print("NEXT STEPS")
        print(f"{'='*70}")
        print("1. Choose 1-2 top priority campaigns to start")
        print("2. Create email templates for each segment")
        print("3. Set up A/B tests for subject lines")
        print("4. Schedule campaigns based on timing suggestions")
        print("5. Prepare follow-up sequences for responders")

        return {
            'total_records': len(self.data),
            'segments': [
                {
                    'name': s.name,
                    'size': s.size,
                    'characteristics': s.characteristics,
                    'campaign_angle': s.campaign_angle,
                    'priority': s.priority
                }
                for s in segments
            ],
            'ideas': [
                {
                    'name': i.name,
                    'target_segment': i.target_segment,
                    'message_angle': i.message_angle,
                    'timing': i.timing,
                    'expected_response': i.expected_response,
                    'ab_test_ideas': i.ab_test_ideas,
                    'priority': i.priority
                }
                for i in ideas
            ]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Campaign Brainstorm - Generate campaign ideas')
    parser.add_argument('path', nargs='?', default='/mnt/hdd/SCRAPER_DATA/',
                       help='Path to CSV file or directory')
    parser.add_argument('--all', action='store_true', help='Load all CSV files in directory')
    parser.add_argument('--focus', help='Focus on specific segment')
    parser.add_argument('--json', action='store_true', help='Output JSON results')

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    brainstormer = CampaignBrainstormer()
    results = brainstormer.brainstorm(path, all_files=args.all)

    if args.json:
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
