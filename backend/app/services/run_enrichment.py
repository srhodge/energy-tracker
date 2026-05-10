"""
CLI runner for the company enrichment service.

Usage:
  python -m app.services.run_enrichment --company-id 2
  python -m app.services.run_enrichment --company-id 2 5 11
  python -m app.services.run_enrichment --tier 1
  python -m app.services.run_enrichment --all
  python -m app.services.run_enrichment --all --dry-run
"""

import argparse
import json
import sys
import os

# Allow running as `python -m app.services.run_enrichment` from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select
from app.config import settings
from app.database import SessionLocal
from app.models import Company, CompanyStatus


def _fmt_result(result: dict) -> None:
    """Pretty-print a single enrichment result."""
    print(f"\n{'='*60}")
    print(f"  {result['company_name']} ({result.get('ticker', '—')})")
    print(f"  company_id={result['company_id']}")
    print(f"{'='*60}")
    for step_name, outcome in result.get("steps", {}).items():
        status = outcome.get("status", "?")
        extra = ""
        if step_name == "employees" and outcome.get("employee_count"):
            extra = f"  → {outcome['employee_count']:,}"
        elif step_name == "hq" and outcome.get("hq_city"):
            extra = f"  → {outcome['hq_city']}, {outcome.get('hq_country', '')}"
        elif step_name == "leadership" and outcome.get("created"):
            roles = [r["role"] for r in outcome["created"]]
            extra = f"  → {', '.join(roles)}"
        elif step_name == "signals" and outcome.get("created"):
            extra = f"  → {len(outcome['created'])} signals"
        elif step_name == "estimate" and outcome.get("total_mid") is not None:
            mid = outcome["total_mid"]
            if mid >= 1e9:
                extra = f"  → ${mid/1e9:.1f}B total mid"
            elif mid >= 1e6:
                extra = f"  → ${mid/1e6:.0f}M total mid"
            else:
                extra = f"  → ${mid:,.0f} total mid"
        print(f"  [{step_name}] {status}{extra}")

    errors = result.get("errors", [])
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    ! {e}")


def main():
    parser = argparse.ArgumentParser(description="Enrich energy companies with web-searched intelligence data.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--company-id", nargs="+", type=int, metavar="ID",
                       help="One or more company IDs to enrich")
    group.add_argument("--tier", type=int, metavar="N",
                       help="Enrich all active companies at data_enrichment_tier=N")
    group.add_argument("--all", action="store_true",
                       help="Enrich all active companies")
    parser.add_argument("--dry-run", action="store_true",
                        help="List companies that would be enriched but don't call the API")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # --- Build company list ---
        if args.company_id:
            all_requested = db.scalars(
                select(Company).where(Company.id.in_(args.company_id))
            ).all()
            companies = [c for c in all_requested if c.status == CompanyStatus.active]
            skipped   = [c for c in all_requested if c.status != CompanyStatus.active]
            not_found  = set(args.company_id) - {c.id for c in all_requested}
            if not_found:
                print(f"WARNING: company IDs not found: {sorted(not_found)}")
            if skipped:
                print(f"Skipping {len(skipped)} non-active companies:")
                for c in skipped:
                    print(f"  - {c.name} (id={c.id}, status={c.status.value})")

        elif args.tier:
            companies = db.scalars(
                select(Company).where(
                    Company.status == CompanyStatus.active,
                    Company.data_enrichment_tier == args.tier,
                )
            ).all()

        else:  # --all
            companies = db.scalars(
                select(Company).where(Company.status == CompanyStatus.active)
            ).all()

        if not companies:
            print("No active companies to enrich.")
            return

        print(f"\nEnriching {len(companies)} active compan{'y' if len(companies)==1 else 'ies'}...")

        if args.dry_run:
            print("\n[DRY RUN — no API calls made]")
            for c in companies:
                tier = c.data_enrichment_tier or "—"
                print(f"  id={c.id:>5}  tier={tier}  {c.name} ({c.ticker or '—'})")
            return

        # --- Run enrichment ---
        from app.services.enrich_company import enrich_company

        all_results = []
        for i, c in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}] {c.name} (id={c.id}) ...")
            try:
                result = enrich_company(c.id, db)
                all_results.append(result)
                _fmt_result(result)
            except ValueError as exc:
                print(f"  SKIP: {exc}")
            except Exception as exc:
                print(f"  ERROR: {exc}")
                if os.environ.get("ENRICH_DEBUG"):
                    import traceback
                    traceback.print_exc()

        # --- Summary ---
        print(f"\n{'='*60}")
        print(f"  ENRICHMENT COMPLETE — {len(all_results)}/{len(companies)} processed")
        print(f"{'='*60}")
        total_errors = sum(len(r.get("errors", [])) for r in all_results)
        if total_errors:
            print(f"  Total step errors across all companies: {total_errors}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
