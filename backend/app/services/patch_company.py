"""
Utility script to push enrichment data into the database via the intelligence API.

Reads a JSON document from a file or stdin and calls:
  PATCH /api/companies/{id}/profile     — profile fields
  POST  /api/companies/{id}/signals     — each signal in the "signals" list
  POST  /api/companies/{id}/leadership  — each record in the "leadership" list

Input JSON shape:
{
  "company_id": 2,
  "profile": {
    "employee_count": 62000,
    "hq_city": "Spring",
    "hq_country": "United States"
  },
  "leadership": [
    {"role": "CEO", "person_name": "Darren Woods", "is_current": true, "signal_score": 1}
  ],
  "signals": [
    {
      "signal_type": "ai_announcement",
      "signal_category": "AI",
      "signal_title": "ExxonMobil announces AI-driven reservoir modelling programme",
      "signal_date": "2025-03-01",
      "spend_impact_direction": "up",
      "score_points": 3,
      "source": "web_search"
    }
  ]
}

Usage:
  python -m app.services.patch_company enrichment.json
  cat enrichment.json | python -m app.services.patch_company -
  python -m app.services.patch_company enrichment.json --base-url http://localhost:8000
  python -m app.services.patch_company enrichment.json --dry-run
"""

import argparse
import json
import sys
import os

# Allow running as `python -m app.services.patch_company` from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass  # stdlib, always available

DEFAULT_BASE_URL = "https://energy-tracker-production-39a1.up.railway.app"


def _request(method: str, url: str, payload: dict | None = None, dry_run: bool = False) -> dict:
    """Make an HTTP request, return parsed JSON response."""
    if dry_run:
        body_preview = json.dumps(payload, default=str)[:120] if payload else ""
        print(f"  [DRY RUN] {method} {url}")
        if body_preview:
            print(f"           {body_preview}{'...' if len(json.dumps(payload or {}, default=str)) > 120 else ''}")
        return {}

    data = json.dumps(payload, default=str).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {method} {url}: {body[:300]}") from None


def patch_company(data: dict, base_url: str, dry_run: bool = False) -> dict:
    """
    Push enrichment data to the API. Returns a summary of actions taken.
    """
    company_id = data.get("company_id")
    if not company_id:
        raise ValueError("Input JSON must include 'company_id'")

    summary: dict = {"company_id": company_id, "profile": None, "signals": [], "leadership": [], "errors": []}

    # ── Profile ───────────────────────────────────────────────────────────────
    profile = data.get("profile")
    if profile:
        url = f"{base_url}/api/companies/{company_id}/profile"
        try:
            result = _request("PATCH", url, profile, dry_run=dry_run)
            summary["profile"] = "updated" if not dry_run else "dry_run"
            print(f"  [profile] {'updated' if not dry_run else 'dry_run'}: {list(profile.keys())}")
        except RuntimeError as e:
            summary["errors"].append(f"profile: {e}")
            print(f"  [profile] ERROR: {e}")
    else:
        print("  [profile] skipped (no profile data)")

    # ── Leadership ────────────────────────────────────────────────────────────
    # Fetch existing records so we can skip duplicates (match on role + person_name)
    existing_leadership: dict[tuple[str, str], int] = {}
    if not dry_run:
        try:
            existing = _request("GET", f"{base_url}/api/companies/{company_id}/leadership?include_past=true")
            if isinstance(existing, list):
                existing_leadership = {
                    (r.get("role", ""), r.get("person_name") or ""): r["id"]
                    for r in existing
                }
        except RuntimeError:
            pass  # proceed without dedup rather than abort

    for rec in data.get("leadership", []):
        role = rec.get("role", "?")
        name = rec.get("person_name") or "?"
        key = (role, name)
        if key in existing_leadership:
            eid = existing_leadership[key]
            summary["leadership"].append({"role": role, "person_name": name, "id": eid, "action": "skipped"})
            print(f"  [leadership] {role}: {name} (exists id={eid} — skipped)")
            continue
        url = f"{base_url}/api/companies/{company_id}/leadership"
        try:
            result = _request("POST", url, rec, dry_run=dry_run)
            created_id = result.get("id", "?") if not dry_run else "dry_run"
            summary["leadership"].append({"role": role, "person_name": name, "id": created_id})
            print(f"  [leadership] {role}: {name} (id={created_id})")
        except RuntimeError as e:
            summary["errors"].append(f"leadership/{role}: {e}")
            print(f"  [leadership] {role} ERROR: {e}")

    # ── Signals ───────────────────────────────────────────────────────────────
    # Fetch existing titles so we can skip duplicates (match on signal_title)
    existing_signal_titles: set[str] = set()
    if not dry_run:
        try:
            existing_sigs = _request("GET", f"{base_url}/api/companies/{company_id}/signals")
            if isinstance(existing_sigs, list):
                existing_signal_titles = {s.get("signal_title") or "" for s in existing_sigs}
        except RuntimeError:
            pass  # proceed without dedup rather than abort

    for sig in data.get("signals", []):
        raw_title = sig.get("signal_title") or "?"
        title = raw_title[:60]
        if raw_title in existing_signal_titles:
            summary["signals"].append({"title": title, "action": "skipped"})
            print(f"  [signal] {title!r} (exists — skipped)")
            continue
        url = f"{base_url}/api/companies/{company_id}/signals"
        try:
            result = _request("POST", url, sig, dry_run=dry_run)
            created_id = result.get("id", "?") if not dry_run else "dry_run"
            summary["signals"].append({"title": title, "id": created_id})
            print(f"  [signal] {title!r} (id={created_id})")
        except RuntimeError as e:
            summary["errors"].append(f"signal/{title}: {e}")
            print(f"  [signal] ERROR: {e}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Push company enrichment data to the intelligence API."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="JSON file path, or '-' to read from stdin (default: stdin)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ENERGY_TRACKER_API_URL", DEFAULT_BASE_URL),
        help=f"API base URL (default: $ENERGY_TRACKER_API_URL or {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without making any API calls",
    )
    args = parser.parse_args()

    # Load JSON input
    if args.input == "-":
        raw = sys.stdin.read()
        source = "stdin"
    else:
        with open(args.input, encoding="utf-8") as f:
            raw = f.read()
        source = args.input

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON from {source}: {e}", file=sys.stderr)
        sys.exit(1)

    # Support both a single object and a list of objects
    records = data if isinstance(data, list) else [data]

    print(f"\nAPI: {args.base_url}{'  [DRY RUN]' if args.dry_run else ''}")

    all_errors: list[str] = []
    for i, record in enumerate(records, 1):
        cid = record.get("company_id", "?")
        print(f"\n[{i}/{len(records)}] company_id={cid}")
        try:
            summary = patch_company(record, base_url=args.base_url, dry_run=args.dry_run)
            all_errors.extend(summary.get("errors", []))
        except ValueError as e:
            print(f"  SKIP: {e}")

    if all_errors:
        print(f"\n{len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  ! {err}")
        sys.exit(1)
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
