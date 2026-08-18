#!/usr/bin/env python3
from pathlib import Path
import argparse, re

PATTERNS = [
    ("command-disguised-as-event", re.compile(r"\b(Send|Dispatch|Notify)(Email|Sms|SMS|Push|Notification)\w*Event\b", re.I)),
    ("direct-send-call", re.compile(r"\b(send_email|send_sms|send_push|sendEmail|sendSms|sendPush)\s*\(", re.I)),
    ("provider-leak", re.compile(r"\b(SendGrid|Twilio|FirebaseMessaging|AmazonSimpleEmailService|SESClient)\b")),
    ("cross-db-smell", re.compile(r"\b(Order|Payment|Booking|User)(Db|Database|Repository|Session)\b")),
    ("exactly-once-claim", re.compile(r"\bexactly[- ]once\b", re.I)),
    ("redis-durable-smell", re.compile(r"\bredis\b.*\b(source of truth|durable notification|exactly.once)\b", re.I)),
]

EXTS = {".py", ".md", ".yaml", ".yml", ".toml", ".sql"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", default=".")
    args = p.parse_args()
    hits = 0
    for f in Path(args.path).rglob("*"):
        if not f.is_file() or f.suffix not in EXTS:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for no, line in enumerate(text.splitlines(), 1):
            for label, rx in PATTERNS:
                if rx.search(line):
                    print(f"{f}:{no}: [{label}] {line.strip()[:220]}")
                    hits += 1
    print(f"\nHeuristic findings: {hits}")
    print("These are review prompts, not proofs. Inspect false positives manually.")

if __name__ == "__main__":
    main()
