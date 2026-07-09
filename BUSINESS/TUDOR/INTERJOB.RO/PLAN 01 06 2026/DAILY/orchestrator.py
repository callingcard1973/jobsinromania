#!/usr/bin/env python3
"""Daily job market roundup orchestrator — phases: validate → create → publish → monitor."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Config
WP_URL = "https://interjob.ro"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "interjob_master"
DB_USER = "tudor"
EURES_BASE = "/opt/ACTIVE/SCRAPER_DATA/csv/EURES"
EURES_COUNTRIES = ["Norway", "Denmark", "Sweden", "Finland", "Germany", "Netherlands", "France"]
WORKSPACE = Path("_workspace")
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")

def setup_workspace():
    """Create workspace for phase outputs."""
    if WORKSPACE.exists():
        backup = Path(f"_workspace_prev_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        WORKSPACE.rename(backup)
        print(f"[Phase 0] Previous workspace backed up: {backup}")
    WORKSPACE.mkdir(exist_ok=True)
    return WORKSPACE

def load_env():
    """Load WP and DB credentials from environment."""
    wp_pass_env = os.getenv("WP_INTERJOB_PASS")
    if not wp_pass_env:
        # Try to load from wp_sites.env
        env_file = "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env"
        if Path(env_file).exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith("WP_INTERJOB_PASS="):
                        wp_pass_env = line.split("=", 1)[1].strip().strip("'\"")
                        break

    db_pass = None
    pgpass_file = Path.home() / ".pgpass"
    if pgpass_file.exists():
        with open(pgpass_file) as f:
            for line in f:
                if line.startswith("localhost") and "tudor" in line:
                    db_pass = line.split(":")[-1].strip()
                    break

    return {
        "wp_user": os.getenv("WP_INTERJOB_USER", "apaminerala"),
        "wp_pass": wp_pass_env,
        "db_pass": db_pass,
    }

def run_agent(agent_name: str, input_data: dict, timeout: int = 60) -> dict:
    """Execute agent via Claude Code agent API (or local Python script)."""
    print(f"\n[Agent] Running {agent_name}...")

    # For now, create a stub that would be replaced by actual agent calling
    # In production, this would use the Claude Code Agent tool
    agent_file = Path(f"agent_{agent_name}.py")
    if agent_file.exists():
        result = subprocess.run(
            [sys.executable, str(agent_file)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return {"error": result.stderr}
        return json.loads(result.stdout)
    else:
        print(f"  [WARNING] Agent script not found: {agent_file}")
        return {"status": "stub", "message": f"Agent {agent_name} not implemented yet"}

def phase1_validate(config: dict) -> dict:
    """Phase 1: Data Validator."""
    print("\n" + "="*70)
    print("PHASE 1: Data Validator")
    print("="*70)

    input_data = {
        "db_host": DB_HOST,
        "db_port": DB_PORT,
        "db_name": DB_NAME,
        "db_user": DB_USER,
        "db_pass": config["db_pass"],
        "eures_base": EURES_BASE,
        "eures_countries": EURES_COUNTRIES,
        "dry_run": False,
    }

    result = run_agent("data_validator", input_data, timeout=60)

    # Save output
    (WORKSPACE / "01_validator_output.json").write_text(json.dumps(result, indent=2))

    if result.get("status") in ["valid", "valid_with_warnings"]:
        print("✅ Validation PASSED")
        if result.get("warnings"):
            for w in result["warnings"]:
                print(f"  ⚠️  {w}")
        return result
    else:
        print(f"❌ Validation FAILED: {result.get('error', 'Unknown error')}")
        return None

def phase2_create(validator_output: dict) -> dict:
    """Phase 2: Content Creator."""
    print("\n" + "="*70)
    print("PHASE 2: Content Creator")
    print("="*70)

    result = run_agent("content_creator", validator_output, timeout=180)

    # Save output
    (WORKSPACE / "02_content_output.json").write_text(json.dumps(result, indent=2))

    if result.get("status") in ["generated", "partial"]:
        print("✅ Content GENERATED")
        if result.get("articles", {}).get("ro"):
            print(f"  RO: {result['articles']['ro'].get('title', 'N/A')[:60]}...")
        if result.get("articles", {}).get("en"):
            print(f"  EN: {result['articles']['en'].get('title', 'N/A')[:60]}...")
        return result
    else:
        print(f"❌ Content generation FAILED: {result.get('error', 'Unknown error')}")
        return None

def phase3_publish(content_output: dict, config: dict) -> dict:
    """Phase 3: Publisher."""
    print("\n" + "="*70)
    print("PHASE 3: Publisher")
    print("="*70)

    input_data = {
        "articles": content_output.get("articles", {}),
        "wp_url": WP_URL,
        "wp_user": config["wp_user"],
        "wp_pass": config["wp_pass"],
        "db_host": DB_HOST,
        "db_name": DB_NAME,
        "db_user": DB_USER,
        "db_pass": config["db_pass"],
        "dry_run": False,
        "force": False,
    }

    result = run_agent("publisher", input_data, timeout=90)

    # Save output
    (WORKSPACE / "03_publisher_output.json").write_text(json.dumps(result, indent=2))

    if result.get("status") in ["published", "partial"]:
        print("✅ Publishing COMPLETED")
        if result.get("results", {}).get("ro", {}).get("post_id"):
            print(f"  RO: post_id={result['results']['ro']['post_id']}")
        if result.get("results", {}).get("en", {}).get("post_id"):
            print(f"  EN: post_id={result['results']['en']['post_id']}")
        return result
    else:
        print(f"❌ Publishing FAILED: {result.get('error', 'Unknown error')}")
        return None

def phase4_monitor(publisher_output: dict, config: dict) -> dict:
    """Phase 4: Monitor (non-blocking)."""
    print("\n" + "="*70)
    print("PHASE 4: Monitor")
    print("="*70)

    results = publisher_output.get("results", {})
    if not results:
        print("⚠️  No published posts to monitor")
        return {"status": "skipped", "reason": "no_posts"}

    input_data = {
        "wp_url": WP_URL,
        "wp_user": config["wp_user"],
        "wp_pass": config["wp_pass"],
        "results": results,
    }

    result = run_agent("monitor", input_data, timeout=45)

    # Save output (non-blocking, so errors don't fail orchestrator)
    (WORKSPACE / "04_monitor_output.json").write_text(json.dumps(result, indent=2))

    print("✅ Monitoring COMPLETED")
    if result.get("alerts"):
        for alert in result["alerts"]:
            print(f"  {alert}")
    return result

def generate_report(validator: dict, content: dict, publisher: dict, monitor: dict) -> dict:
    """Generate final completion report."""
    report = {
        "orchestration_status": "success",
        "timestamp": datetime.now().isoformat(),
        "phases_completed": 4,
        "results": {
            "validation": {
                "status": validator.get("status"),
                "anofm_count": validator.get("anofm_total"),
                "eures_count": validator.get("eures_total"),
                "warnings": validator.get("warnings", []),
            },
            "content": {
                "status": content.get("status"),
                "ro_title": content.get("articles", {}).get("ro", {}).get("title"),
                "en_title": content.get("articles", {}).get("en", {}).get("title"),
            },
            "publishing": {
                "status": publisher.get("status"),
                "ro_post_id": publisher.get("results", {}).get("ro", {}).get("post_id"),
                "en_post_id": publisher.get("results", {}).get("en", {}).get("post_id"),
            },
            "monitoring": {
                "status": monitor.get("status"),
                "summary": monitor.get("summary"),
            },
        },
    }

    (WORKSPACE / "final_report.json").write_text(json.dumps(report, indent=2))
    return report

def main():
    parser = argparse.ArgumentParser(description="Daily roundup orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Validate + generate, don't publish")
    parser.add_argument("--force", action="store_true", help="Publish even if today's lang exists")
    parser.add_argument("--lang", choices=["ro", "en", "both"], default="both", help="Language to publish")
    args = parser.parse_args()

    print(f"🚀 Daily Roundup Orchestrator — {datetime.now().isoformat()}")
    print(f"   Workspace: {WORKSPACE}")

    setup_workspace()
    config = load_env()

    if not config["wp_pass"] or not config["db_pass"]:
        print("❌ ERROR: Missing WP_INTERJOB_PASS or DB password in ~/.pgpass")
        sys.exit(1)

    # Phase 1: Validate
    validator_output = phase1_validate(config)
    if not validator_output:
        print("\n❌ ABORT: Validation failed")
        sys.exit(1)

    # Phase 2: Create
    content_output = phase2_create(validator_output)
    if not content_output:
        print("\n❌ ABORT: Content generation failed")
        sys.exit(1)

    # Phase 3: Publish (skip if --dry-run)
    if args.dry_run:
        print("\n[DRY RUN] Skipping publish and monitor phases")
        publisher_output = {"status": "dry_run", "results": {}}
        monitor_output = {"status": "skipped"}
    else:
        publisher_output = phase3_publish(content_output, config)
        if not publisher_output:
            print("\n⚠️  WARN: Publishing failed, skipping monitor")
            monitor_output = {"status": "skipped"}
        else:
            # Phase 4: Monitor (non-blocking)
            monitor_output = phase4_monitor(publisher_output, config)

    # Final report
    report = generate_report(validator_output, content_output, publisher_output, monitor_output)

    print("\n" + "="*70)
    print("✅ ORCHESTRATION COMPLETE")
    print("="*70)
    print(json.dumps(report, indent=2))

    # Log to file
    log_file = LOG_DIR / "daily_roundup.log"
    log_file.parent.mkdir(exist_ok=True, parents=True)
    with open(log_file, "a") as f:
        f.write(f"\n{json.dumps(report)}\n")

if __name__ == "__main__":
    main()
