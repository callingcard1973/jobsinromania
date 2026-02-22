#!/usr/bin/env python3
"""
Token Reduction Dashboard — Weekly optimization report and trend analysis.

Tracks:
  1. Files optimized per week
  2. Tokens saved per optimization
  3. Cumulative savings across all machines
  4. Trend analysis (improving/stable/declining)
  5. Recommendations for further optimization

Usage:
  python reduction_dashboard.py              # Show weekly summary
  python reduction_dashboard.py --weekly     # Generate weekly report
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
REPORT_FILE = LOG_DIR / f"reduction_{datetime.now().strftime('%Y%m%d')}.json"
STATS_FILE = LOG_DIR / "optimizer_stats.json"


class ReductionDashboard:
    def __init__(self):
        self.log_dir = LOG_DIR
        self.report_file = REPORT_FILE

    def load_all_reports(self) -> List[Dict]:
        """Load all daily reports to analyze trends"""
        reports = []
        for report_file in sorted(self.log_dir.glob("reduction_*.json")):
            try:
                with open(report_file, 'r') as f:
                    reports.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        return reports

    def load_optimizer_stats(self) -> Dict:
        """Load latest optimizer statistics"""
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"total_files": 0, "optimized": 0, "tokens_saved": 0, "files": {}}

    def calculate_trend(self, reports: List[Dict]) -> str:
        """Analyze trend direction"""
        if len(reports) < 2:
            return "insufficient_data"

        recent_savings = sum(r.get("tokens_saved", 0) for r in reports[-7:])
        older_savings = sum(r.get("tokens_saved", 0) for r in reports[-14:-7]) if len(reports) >= 14 else recent_savings

        if recent_savings > older_savings * 1.1:
            return "improving"
        elif recent_savings < older_savings * 0.9:
            return "declining"
        else:
            return "stable"

    def get_top_bloated_files(self, stats: Dict) -> List[tuple]:
        """Get top 5 most bloated files"""
        files = stats.get("files", {})
        bloated = []
        for filepath, data in files.items():
            tokens_before = data.get("tokens_before", 0)
            tokens_after = data.get("tokens_after", 0)
            savings = tokens_before - tokens_after
            if savings > 0:
                bloated.append((filepath, savings))
        return sorted(bloated, key=lambda x: x[1], reverse=True)[:5]

    def get_recommendations(self, stats: Dict, reports: List[Dict]) -> List[str]:
        """Generate recommendations for further optimization"""
        recommendations = []

        # Check for still-bloated files
        files = stats.get("files", {})
        bloated_count = sum(1 for data in files.values() if data.get("tokens_before", 0) > 1500)
        if bloated_count > 0:
            recommendations.append(f"[WARN] {bloated_count} files still exceed 1500 tokens — manual review needed")

        # Check optimization rate
        if stats.get("optimized", 0) < stats.get("total_files", 0) * 0.5:
            recommendations.append("[INFO] <50% of files optimized — consider expanding auto-trim rules")

        # Check trend
        trend = self.calculate_trend(reports)
        if trend == "declining":
            recommendations.append("[WARN] Token savings declining — files may be re-bloating, review auto-trim schedule")
        elif trend == "improving":
            recommendations.append("[OK] Token savings improving — continue current optimization strategy")

        # Suggest next steps
        if stats.get("tokens_saved", 0) > 10000:
            recommendations.append("[OK] >10K tokens saved — consider deploying to production cache layer")

        return recommendations if recommendations else ["[OK] All systems nominal — no action required"]

    def generate_report(self) -> Dict:
        """Generate comprehensive reduction report"""
        stats = self.load_optimizer_stats()
        reports = self.load_all_reports()

        report = {
            "generated": datetime.now().isoformat(),
            "summary": {
                "total_files": stats.get("total_files", 0),
                "optimized": stats.get("optimized", 0),
                "tokens_saved_total": stats.get("tokens_saved", 0),
                "tokens_saved_avg_per_file": (
                    stats.get("tokens_saved", 0) // stats.get("optimized", 1)
                    if stats.get("optimized", 0) > 0 else 0
                )
            },
            "trend": self.calculate_trend(reports),
            "top_bloated": [
                {"file": f[0], "tokens_saved": f[1]}
                for f in self.get_top_bloated_files(stats)
            ],
            "recommendations": self.get_recommendations(stats, reports),
            "weekly_stats": {
                "reports_this_week": len([r for r in reports if self.is_this_week(r.get("generated"))]),
                "total_reports": len(reports)
            }
        }
        return report

    def is_this_week(self, date_str: str) -> bool:
        """Check if date is within this week"""
        try:
            date = datetime.fromisoformat(date_str)
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            return week_ago <= date <= now
        except (ValueError, TypeError):
            return False

    def display_report(self, report: Dict):
        """Pretty-print report"""
        print("\n[TOKEN REDUCTION DASHBOARD]")
        print(f"Generated: {report['generated']}\n")

        summary = report["summary"]
        print("[SUMMARY]")
        print(f"  Total files scanned:     {summary['total_files']}")
        print(f"  Files optimized:         {summary['optimized']}")
        print(f"  Total tokens saved:      {summary['tokens_saved_total']:,}")
        print(f"  Avg tokens/file:         {summary['tokens_saved_avg_per_file']}")

        print(f"\n[TREND]")
        trend = report["trend"]
        trend_symbol = {"improving": "[UP]", "stable": "[--]", "declining": "[DN]", "insufficient_data": "[?]"}
        print(f"  Status: {trend_symbol.get(trend, '?')} {trend}")

        if report["top_bloated"]:
            print(f"\n[TOP OPTIMIZED FILES]")
            for item in report["top_bloated"]:
                print(f"  {item['tokens_saved']:6,d} tokens — {item['file'][:60]}")

        print(f"\n[RECOMMENDATIONS]")
        for rec in report["recommendations"]:
            print(f"  {rec}")

        print(f"\n[WEEKLY STATS]")
        weekly = report["weekly_stats"]
        print(f"  Reports this week:       {weekly['reports_this_week']}")
        print(f"  Total reports:           {weekly['total_reports']}")

        print()

    def save_report(self, report: Dict):
        """Save report as JSON"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        with open(self.report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved: {self.report_file}")

    def run(self, save=False):
        """Generate and display report"""
        report = self.generate_report()
        self.display_report(report)
        if save:
            self.save_report(report)


def main():
    import sys
    save = "--weekly" in sys.argv or "--save" in sys.argv

    dashboard = ReductionDashboard()
    dashboard.run(save=save)


if __name__ == '__main__':
    main()
