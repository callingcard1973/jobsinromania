#!/usr/bin/env python3
import sys
import argparse

sys.path.insert(0, "/opt/ASTERISK/autodialer/scripts")

from config import CAMPAIGNS_DIR, CONTEXT_SIMPLE, CONTEXT_IVR, CONTEXT_SURVEY
from dialer import CampaignDialer, list_campaigns, create_campaign
from tts_generator import generate_tts, check_dependencies
from call_generator import generate_call_file, submit_call


def show_status(campaign_name=None):
    if campaign_name:
        try:
            dialer = CampaignDialer(campaign_name)
            st = dialer.status()
            print(f"\n=== {st["campaign"]} ===")
            print(f"Message: {st["message"]}")
            print(f"Total contacts: {st["total_contacts"]}")
            print(f"Pending: {st["pending"]}")
            print(f"Completed: {st.get("completed", 0)}")
            print(f"Failed: {st.get("failed", 0)}")
            print(f"Retry queue: {st.get("retry", 0)}")
            if st.get("completion_rate"):
                print(f"Completion rate: {st["completion_rate"]}%")
        except ValueError as e:
            print(f"Error: {e}")
    else:
        campaigns = list_campaigns()
        if not campaigns:
            print("No campaigns found.")
            print("Create one: python3 autodialer.py create CAMPAIGN_NAME")
            return
        
        print("\n=== Auto-Dialer Campaigns ===\n")
        print(f"{"Campaign":<20} {"Total":<8} {"Done":<8} {"Pending":<8} {"Rate":<8}")
        print("-" * 60)
        
        for cname in campaigns:
            try:
                dialer = CampaignDialer(cname)
                st = dialer.status()
                rate = st.get("completion_rate", 0)
                print(f"{cname:<20} {st["total_contacts"]:<8} "
                      f"{st.get("completed", 0):<8} {st["pending"]:<8} "
                      f"{rate:.1f}%")
            except Exception as e:
                print(f"{cname:<20} Error: {e}")


def run_campaign(campaign_name, limit=None, context=CONTEXT_SIMPLE, test=False, force=False):
    try:
        dialer = CampaignDialer(campaign_name)
        dialer.run(limit=limit, context=context, dry_run=test, respect_hours=not force)
    except ValueError as e:
        print(f"Error: {e}")


def single_call(phone, message="test"):
    print(f"Generating call to {phone}...")
    call_file = generate_call_file(phone=phone, message=message, context=CONTEXT_SIMPLE)
    print(f"Call file: {call_file}")
    with open(call_file, "r") as f:
        print(f.read())
    confirm = input("\nSubmit call? [y/N]: ")
    if confirm.lower() == "y":
        if submit_call(call_file):
            print("Call submitted to Asterisk")
        else:
            print("Failed to submit")


def main():
    parser = argparse.ArgumentParser(description="Auto-Dialer Skill")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    status_p = subparsers.add_parser("status", help="Show campaign status")
    status_p.add_argument("campaign", nargs="?", help="Campaign name")
    
    create_p = subparsers.add_parser("create", help="Create new campaign")
    create_p.add_argument("name", help="Campaign name")
    
    run_p = subparsers.add_parser("run", help="Run campaign")
    run_p.add_argument("campaign", help="Campaign name")
    run_p.add_argument("--limit", type=int, help="Max calls")
    run_p.add_argument("--context", choices=["simple", "ivr", "survey"], default="simple")
    run_p.add_argument("--force", action="store_true", help="Ignore business hours")
    
    test_p = subparsers.add_parser("test", help="Test campaign (dry run)")
    test_p.add_argument("campaign", help="Campaign name")
    test_p.add_argument("--limit", type=int, default=5, help="Max calls")
    
    tts_p = subparsers.add_parser("tts", help="Generate TTS audio")
    tts_p.add_argument("text", help="Text to convert")
    tts_p.add_argument("-o", "--output", default="message", help="Output filename")
    tts_p.add_argument("-e", "--engine", choices=["pico", "espeak", "gtts", "edge"])
    tts_p.add_argument("-l", "--language", default="en-US", help="Language")
    
    call_p = subparsers.add_parser("call", help="Make single test call")
    call_p.add_argument("phone", help="Phone number")
    call_p.add_argument("--message", default="test", help="Message to play")
    
    subparsers.add_parser("check-tts", help="Check available TTS engines")
    
    args = parser.parse_args()
    
    if args.command == "status":
        show_status(args.campaign)
    elif args.command == "create":
        create_campaign(args.name)
    elif args.command == "run":
        ctx = {"simple": CONTEXT_SIMPLE, "ivr": CONTEXT_IVR, "survey": CONTEXT_SURVEY}
        run_campaign(args.campaign, limit=args.limit, context=ctx[args.context], force=args.force)
    elif args.command == "test":
        run_campaign(args.campaign, limit=args.limit, test=True)
    elif args.command == "tts":
        generate_tts(text=args.text, output_name=args.output, engine=args.engine, language=args.language)
    elif args.command == "call":
        single_call(args.phone, args.message)
    elif args.command == "check-tts":
        available = check_dependencies()
        print("Available TTS engines:", available if available else "None")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
