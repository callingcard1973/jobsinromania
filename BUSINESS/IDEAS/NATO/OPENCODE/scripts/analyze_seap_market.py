#!/usr/bin/env python3
"""Analyze SEAP food contracts market"""

import csv
import sys
from collections import defaultdict
from datetime import datetime


def analyze_seap_food_market():
    input_file = (
        "/opt/ACTIVE/IDEAS/FOOD/SUPERMARKETS_CLAUDE/DATA/seap_food_winners_all.csv"
    )

    # Data structures
    cpv_analysis = defaultdict(
        lambda: {"count": 0, "total_ron": 0, "total_eur": 0, "winners": set()}
    )
    buyer_analysis = defaultdict(
        lambda: {"count": 0, "total_ron": 0, "total_eur": 0, "cpvs": set()}
    )
    winner_analysis = defaultdict(
        lambda: {"count": 0, "total_ron": 0, "total_eur": 0, "buyers": set()}
    )

    currency_conv = {"RON": 1.0, "EUR": 5.0, "USD": 4.5}  # Approximate

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                cpv = row.get("cpv_code", "").strip()
                winner = row.get("winner_name", "").strip()
                buyer = row.get("buyer_name", "").strip()
                currency = row.get("currency", "").strip().upper()
                value_str = row.get("value", "0").replace(",", "").strip()

                # Skip if no CPV or value
                if not cpv or not value_str or value_str == "":
                    continue

                try:
                    value_orig = float(value_str)
                    conv_rate = currency_conv.get(
                        currency, 5.0
                    )  # Default to EUR if unknown
                    value_ron = value_orig * conv_rate

                    # CPV analysis
                    cpv_analysis[cpv]["count"] += 1
                    cpv_analysis[cpv]["total_ron"] += value_ron
                    if currency == "EUR":
                        cpv_analysis[cpv]["total_eur"] += value_orig
                    cpv_analysis[cpv]["winners"].add(winner)

                    # Buyer analysis
                    buyer_analysis[buyer]["count"] += 1
                    buyer_analysis[buyer]["total_ron"] += value_ron
                    if currency == "EUR":
                        buyer_analysis[buyer]["total_eur"] += value_orig
                    buyer_analysis[buyer]["cpvs"].add(cpv)

                    # Winner analysis
                    winner_analysis[winner]["count"] += 1
                    winner_analysis[winner]["total_ron"] += value_ron
                    if currency == "EUR":
                        winner_analysis[winner]["total_eur"] += value_orig
                    winner_analysis[winner]["buyers"].add(buyer)

                except (ValueError, ZeroDivisionError):
                    continue

        # Calculate totals
        total_contracts = sum(c["count"] for c in cpv_analysis.values())
        total_value_ron = sum(c["total_ron"] for c in cpv_analysis.values())
        total_value_eur = sum(c["total_eur"] for c in cpv_analysis.values())

        # Print summary
        print("=" * 80)
        print("SEAP FOOD CONTRACTS MARKET ANALYSIS")
        print("=" * 80)
        print(f"\nTotal Contracts: {total_contracts:,}")
        print(f"Total Value: {total_value_ron:,.0f} RON ({total_value_eur:,.0f} EUR)")
        print(
            f"Average Contract Value: {total_value_ron / total_contracts:,.0f} RON ({total_value_eur / total_contracts:,.0f} EUR)"
        )

        # Top CPV codes
        print("\n" + "=" * 80)
        print("TOP 20 CPV CODES BY CONTRACT COUNT")
        print("=" * 80)
        sorted_cpvs = sorted(
            cpv_analysis.items(), key=lambda x: x[1]["count"], reverse=True
        )[:20]
        print(
            f"{'CPV Code':<15} {'Count':>8} {'Total RON':>18} {'Total EUR':>15} {'Avg RON':>12}"
        )
        print("-" * 80)
        for cpv, stats in sorted_cpvs:
            avg = stats["total_ron"] / stats["count"] if stats["count"] > 0 else 0
            print(
                f"{cpv:<15} {stats['count']:>8} {stats['total_ron']:>15,.0f} {stats['total_eur']:>11,.0f} {avg:>10,.0f}"
            )

        # High-value CPV codes
        print("\n" + "=" * 80)
        print("TOP 15 CPV CODES BY TOTAL VALUE (RON)")
        print("=" * 80)
        sorted_by_value = sorted(
            cpv_analysis.items(), key=lambda x: x[1]["total_ron"], reverse=True
        )[:15]
        print(
            f"{'CPV Code':<15} {'Total RON':>18} {'Total EUR':>15} {'Count':>8} {'Avg RON':>12}"
        )
        print("-" * 80)
        for cpv, stats in sorted_by_value:
            avg = stats["total_ron"] / stats["count"] if stats["count"] > 0 else 0
            print(
                f"{cpv:<15} {stats['total_ron']:>15,.0f} {stats['total_eur']:>11,.0f} {stats['count']:>8} {avg:>10,.0f}"
            )

        # Major buyers
        print("\n" + "=" * 80)
        print("TOP 15 BUYERS BY CONTRACT VALUE")
        print("=" * 80)
        sorted_buyers = sorted(
            buyer_analysis.items(), key=lambda x: x[1]["total_ron"], reverse=True
        )[:15]
        print(f"{'Buyer':<50} {'Total RON':>18} {'Count':>6}")
        print("-" * 80)
        for buyer, stats in sorted_buyers:
            buyer_short = buyer[:48] if buyer else "Unknown"
            print(f"{buyer_short:<50} {stats['total_ron']:>15,.0f} {stats['count']:>6}")

        # Major winners
        print("\n" + "=" * 80)
        print("TOP 15 SUPPLIERS BY TOTAL VALUE")
        print("=" * 80)
        sorted_winners = sorted(
            winner_analysis.items(), key=lambda x: x[1]["total_ron"], reverse=True
        )[:15]
        print(
            f"{'Supplier':<40} {'Total RON':>18} {'Total EUR':>12} {'Count':>6} {'Buyers':>6}"
        )
        print("-" * 80)
        for winner, stats in sorted_winners:
            winner_short = winner[:38] if winner else "Unknown"
            print(
                f"{winner_short:<40} {stats['total_ron']:>15,.0f} {stats['total_eur']:>10,.0f} {stats['count']:>6} {len(stats['buyers']):>6}"
            )

        # Contract size distribution
        print("\n" + "=" * 80)
        print("CONTRACT SIZE DISTRIBUTION")
        print("=" * 80)

        size_ranges = [
            ("<5K EUR", 0, 5000),
            ("5K-10K EUR", 5000, 10000),
            ("10K-25K EUR", 10000, 25000),
            ("25K-50K EUR", 25000, 50000),
            ("50K-100K EUR", 50000, 100000),
            ("100K-250K EUR", 100000, 250000),
            ("250K-500K EUR", 250000, 500000),
            (">500K EUR", 500000, float("inf")),
        ]

        size_counts = defaultdict(int)
        size_values = defaultdict(float)

        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                currency = row.get("currency", "").upper()
                value_str = row.get("value", "0").replace(",", "").strip()
                try:
                    if value_str == "":
                        continue
                    value = float(value_str)
                    if currency != "EUR":
                        continue

                    for label, low, high in size_ranges:
                        if low <= value < high:
                            size_counts[label] += 1
                            size_values[label] += value
                            break
                except (ValueError, ZeroDivisionError):
                    continue

        for label, low, high in size_ranges:
            count = size_counts[label]
            total = size_values[label]
            avg = total / count if count > 0 else 0
            pct = (count / total_contracts * 100) if total_contracts > 0 else 0
            print(
                f"{label:<15} Count: {count:>6} ({pct:>5.1f}%) | Total: {total:>12,.0f} EUR | Avg: {avg:>8,.0f} EUR"
            )

        return {
            "total_contracts": total_contracts,
            "total_value_ron": total_value_ron,
            "total_value_eur": total_value_eur,
            "cpv_codes": len(cpv_analysis),
            "buyers": len(buyer_analysis),
            "winners": len(winner_analysis),
        }

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    analyze_seap_food_market()
