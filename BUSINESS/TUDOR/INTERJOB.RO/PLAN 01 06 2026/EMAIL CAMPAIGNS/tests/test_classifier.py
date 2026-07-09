#!/usr/bin/env python3
"""Regression test for the reply classifier — guards the opt-out / bounce false-positive
bug class (quoted footers, 'nu mai', 'stop ' substrings) that 3 reviews kept catching."""
import sys, os
# find universal_reply_handler whether on raspibig (/opt) or alongside the repo copy
sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import universal_reply_handler as h

# (from_addr, subject, body, expected_label)
CASES = [
    # --- real opt-outs ---
    ("a@firma.no", "Re: workers", "Please unsubscribe me from your list.", "opt_out"),
    ("b@firma.ro", "RE: oferta", "Va rog scoateti-ma de pe lista.", "opt_out"),
    ("c@x.no", "stop", "Please stop sending me these emails.", "opt_out"),
    # --- the BUG CLASS: must NOT be opt_out despite quoted footer / substrings ---
    ("lead@bygg.no", "Re: Skilled EU construction workers",
     "Yes, please send profiles for 5 carpenters in Oslo.\n\nOn Mon someone wrote:\n> reply STOP or email unsubscribe@buildjobs.eu", "interested"),
    ("d@firma.ro", "Re: muncitori", "Nu mai avem nevoie momentan, dar poate la primavara.", "neutral"),
    ("e@bus.no", "Re: transport", "Our office is near the bus stop, send details please.", "interested"),
    # --- workers ---
    ("worker@gmail.com", "Application", "I am applying for a construction job, I have experience and am ready to join.", "worker_application"),
    ("w2@gmail.com", "CV", "Please find my attached CV, I am looking for work in Norway.", "worker_application"),
    # --- employer leads ---
    ("hr@ncc.no", "Re: workers", "Please send profiles and rates for 10 builders.", "interested"),
    ("f@firma.no", "Re: tilbud", "Vi trenger folk, kontakt oss.", "interested"),
    # --- auto-replies ---
    ("g@firma.no", "Automatisk svar", "Jeg er ute av kontoret til mandag.", "auto_reply"),
    ("h@firma.ro", "Concediu", "Sunt in concediu de odihna pana pe 1.", "auto_reply"),
    ("i@firma.se", "Ticket", "Your ticket received and logged, ref: 123.", "auto_reply"),
    # --- ignore (noise senders) ---
    ("noreply@system.example.com", "notification", "anything", "ignore"),
    ("account-alerts@t.brevo.com", "Security alert", "new login to your account", "ignore"),
    # --- neutral business ---
    ("j@firma.no", "Re: samarbeid", "Takk for henvendelsen, vi vurderer det.", "neutral"),
    # --- regression: worker pleas + employer catalog + Norwegian OOO (the Zeeshan class) ---
    ("mjani1190@gmail.com", "Re: Thank you for your message",
     "Sir i am from Pakistan stay in Malaysia as worker, i want to work with you, please give me chance", "worker_application"),
    ("a@bygg.no", "Re: workers",
     "Yes please send the catalog.\n\nOn Mon someone wrote:\n> unsubscribe reply STOP", "interested"),
    ("x@firma.no", "Automatisk svar", "Jeg er ute av kontoret til mandag.", "auto_reply"),
    ("d@firma.ro", "Re: muncitori", "Nu mai avem nevoie momentan, multumesc.", "neutral"),
]


def test_classify():
    """pytest entrypoint — asserts every regression case classifies as expected."""
    fails = [(frm, subj[:28], exp, h.classify(frm, subj, body))
             for frm, subj, body, exp in CASES if h.classify(frm, subj, body) != exp]
    assert not fails, "misclassified: " + "; ".join(
        f"{frm} '{subj}' expected={exp} got={got}" for frm, subj, exp, got in fails)


def main():
    ok = 0
    fails = []
    for frm, subj, body, exp in CASES:
        got = h.classify(frm, subj, body)
        if got == exp:
            ok += 1
        else:
            fails.append((frm, subj[:28], exp, got))
    print(f"classifier regression: {ok}/{len(CASES)} passed")
    for frm, subj, exp, got in fails:
        print(f"  FAIL  {frm:28} '{subj}'  expected={exp}  got={got}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
