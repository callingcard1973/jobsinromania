#!/usr/bin/env python3
"""
Trim Campaigns to Exactly 6K Romanian Contacts Each
Remove excess contacts to reach target, keeping highest quality
"""

import sqlite3
import logging
from datetime import datetime

class CampaignTrimmer:
    def __init__(self):
        self.campaigns = {
            'VIRGIL': '/opt/EMAIL/CAMPAIGNS/VIRGIL/virgil.db',
            'ELENA': '/opt/EMAIL/CAMPAIGNS/ELENA/elena.db',
            'LUCIAN': '/opt/EMAIL/CAMPAIGNS/LUCIAN/lucian.db',
            'TUDOR': '/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db'
        }

        self.target_per_campaign = 6000

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_current_counts(self):
        """Get current contact counts"""
        counts = {}

        for campaign, db_path in self.campaigns.items():
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM contacts")
                counts[campaign] = cursor.fetchone()[0]
                conn.close()
            except Exception as e:
                self.logger.error(f"Error counting {campaign}: {e}")
                counts[campaign] = 0

        return counts

    def trim_campaign_to_target(self, campaign, db_path, target_count):
        """Trim campaign to target count, keeping best quality contacts"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get current count
            cursor.execute("SELECT COUNT(*) FROM contacts")
            current_count = cursor.fetchone()[0]

            if current_count <= target_count:
                self.logger.info(f"{campaign}: {current_count} contacts (no trimming needed)")
                conn.close()
                return 0

            to_remove = current_count - target_count

            # Quality scoring criteria (higher = better):
            # 1. Has company name (not empty/null)
            # 2. Has contact name
            # 3. Has phone
            # 4. Has city
            # 5. Email length (longer often better)
            # 6. Recently added (prefer newer)

            quality_query = """
            SELECT id,
                   email,
                   company,
                   contact_name,
                   phone,
                   city,
                   added_at,
                   (CASE WHEN company IS NOT NULL AND company != '' THEN 2 ELSE 0 END +
                    CASE WHEN contact_name IS NOT NULL AND contact_name != '' THEN 2 ELSE 0 END +
                    CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END +
                    CASE WHEN city IS NOT NULL AND city != '' THEN 1 ELSE 0 END +
                    CASE WHEN LENGTH(email) > 15 THEN 1 ELSE 0 END) as quality_score
            FROM contacts
            ORDER BY quality_score ASC, added_at ASC
            LIMIT ?
            """

            # Get lowest quality contacts to remove
            cursor.execute(quality_query, (to_remove,))
            contacts_to_remove = cursor.fetchall()

            # Remove them
            removed_count = 0
            for contact in contacts_to_remove:
                contact_id = contact[0]
                cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
                removed_count += 1

            conn.commit()

            # Verify final count
            cursor.execute("SELECT COUNT(*) FROM contacts")
            final_count = cursor.fetchone()[0]

            conn.close()

            self.logger.info(f"{campaign}: {current_count} → {final_count} (removed {removed_count} lowest quality)")
            return removed_count

        except Exception as e:
            self.logger.error(f"Error trimming {campaign}: {e}")
            return 0

    def analyze_quality_distribution(self, campaign, db_path):
        """Analyze quality distribution before trimming"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Quality analysis
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN company IS NOT NULL AND company != '' THEN 1 ELSE 0 END) as has_company,
                    SUM(CASE WHEN contact_name IS NOT NULL AND contact_name != '' THEN 1 ELSE 0 END) as has_contact,
                    SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END) as has_phone,
                    SUM(CASE WHEN city IS NOT NULL AND city != '' THEN 1 ELSE 0 END) as has_city,
                    AVG(LENGTH(email)) as avg_email_length
                FROM contacts
            """)

            stats = cursor.fetchone()

            self.logger.info(f"{campaign} quality: {stats[0]} total, "
                           f"company: {stats[1]}, contact: {stats[2]}, "
                           f"phone: {stats[3]}, city: {stats[4]}, "
                           f"avg_email_len: {stats[5]:.1f}")

            conn.close()
            return stats

        except Exception as e:
            self.logger.error(f"Error analyzing {campaign}: {e}")
            return None

    def trim_all_campaigns(self):
        """Trim all campaigns to target number"""
        self.logger.info(f"=== TRIMMING CAMPAIGNS TO {self.target_per_campaign} EACH ===")

        # Step 1: Get current counts
        current_counts = self.get_current_counts()
        self.logger.info(f"Current counts: {current_counts}")

        # Step 2: Analyze quality before trimming
        self.logger.info("Step 2: Analyzing contact quality...")
        for campaign, db_path in self.campaigns.items():
            self.analyze_quality_distribution(campaign, db_path)

        # Step 3: Calculate what needs to be removed
        total_to_remove = 0
        removal_plan = {}

        for campaign, current in current_counts.items():
            if current > self.target_per_campaign:
                to_remove = current - self.target_per_campaign
                removal_plan[campaign] = to_remove
                total_to_remove += to_remove
            else:
                removal_plan[campaign] = 0

        self.logger.info(f"Removal plan: {removal_plan}")
        self.logger.info(f"Total contacts to remove: {total_to_remove}")

        if total_to_remove == 0:
            self.logger.info("All campaigns already at or below target!")
            return current_counts

        # Step 4: Trim each campaign
        self.logger.info("Step 4: Trimming campaigns...")
        final_counts = {}

        for campaign, to_remove in removal_plan.items():
            if to_remove > 0:
                removed = self.trim_campaign_to_target(
                    campaign,
                    self.campaigns[campaign],
                    self.target_per_campaign
                )
                final_counts[campaign] = current_counts[campaign] - removed
            else:
                final_counts[campaign] = current_counts[campaign]

        # Step 5: Verify final counts
        self.logger.info("=== FINAL VERIFICATION ===")
        verified_counts = self.get_current_counts()

        total_final = sum(verified_counts.values())
        total_removed = sum(current_counts.values()) - total_final

        for campaign in self.campaigns.keys():
            original = current_counts[campaign]
            final = verified_counts[campaign]
            removed = original - final

            self.logger.info(f"{campaign}: {original} → {final} (-{removed})")

        self.logger.info(f"TOTAL: {sum(current_counts.values())} → {total_final} (-{total_removed})")

        return verified_counts

def main():
    trimmer = CampaignTrimmer()

    print("✂️  TRIMMING CAMPAIGNS TO 6,000 ROMANIAN CONTACTS EACH")
    print("=" * 60)

    result = trimmer.trim_all_campaigns()

    print(f"\n📊 FINAL RESULTS:")
    total_final = sum(result.values())

    for campaign, count in result.items():
        target_met = "✅" if count == 6000 else f"❌ ({abs(6000-count)} {'over' if count > 6000 else 'under'})"
        print(f"  {campaign}: {count:,} contacts {target_met}")

    print(f"\n📈 TOTAL: {total_final:,} contacts across all campaigns")
    print(f"🎯 TARGET: {4 * 6000:,} contacts (6K each × 4 campaigns)")

    if total_final == 24000:
        print("✅ ALL CAMPAIGNS PERFECTLY BALANCED!")
    else:
        diff = total_final - 24000
        print(f"⚠️ Difference: {diff:+,} contacts from target")

if __name__ == "__main__":
    main()