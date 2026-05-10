"""
CLI runner for the spend estimation engine.

Usage:
  python -m app.services.run_estimates --tier 1
  python -m app.services.run_estimates --tier 1 2
  python -m app.services.run_estimates --company-id 3
  python -m app.services.run_estimates --company-id 3 7 12
  python -m app.services.run_estimates --all
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from sqlalchemy import select
from app.database import SessionLocal
from app.models import Company, CompanyStatus
from app.services.spend_estimator import estimate


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def run(company_ids: list[int], tier_map: dict[int, int]) -> None:
    ok = err = 0
    rows = []

    with SessionLocal() as db:
        for cid in company_ids:
            try:
                result = estimate(cid, db)
                result["tier"] = tier_map.get(cid, "-")
                rows.append(result)
                ok += 1
            except Exception as e:
                print(f"  ERROR company_id={cid}: {e}", file=sys.stderr)
                err += 1

    if not rows:
        print("No estimates produced.")
        return

    print(
        f"\n{'Company':<45} {'T':>2} {'Conf':<7} {'Sub-sector':<35} "
        f"{'IT mid':>10} {'OT mid':>10} {'Dig mid':>10} {'AI mid':>10} "
        f"{'Total mid':>12} {'WWT high':>12}"
    )
    print("-" * 168)

    for r in sorted(rows, key=lambda x: -(x["total_spend"]["mid"] or 0)):
        print(
            f"  {r['company_name']:<43} "
            f"{str(r['tier']):>2} "
            f"{r['confidence_level']:<7} "
            f"{(r['sub_sector'] or 'unknown'):<35} "
            f"{_fmt(r['it_spend']['mid']):>10} "
            f"{_fmt(r['ot_spend']['mid']):>10} "
            f"{_fmt(r['digital_spend']['mid']):>10} "
            f"{_fmt(r['ai_spend']['mid']):>10} "
            f"{_fmt(r['total_spend']['mid']):>12} "
            f"{_fmt(r['wwt_addressable']['high']):>12}"
        )

    print()
    print(f"  Estimated: {ok}   Errors: {err}")

    totals = [r["total_spend"]["mid"] for r in rows if r["total_spend"]["mid"] is not None]
    if totals:
        grand_total = sum(totals)
        grand_wwt   = sum(r["wwt_addressable"]["high"] or 0 for r in rows)
        print(f"  Grand total mid:  {_fmt(grand_total)}")
        print(f"  Grand WWT high:   {_fmt(grand_wwt)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Run spend estimates")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tier",       type=int, nargs="+", metavar="N",
                       help="Run all companies at enrichment tier(s)")
    group.add_argument("--company-id", type=int, nargs="+", metavar="ID",
                       help="Run specific company IDs")
    group.add_argument("--all",        action="store_true",
                       help="Run all companies")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.company_id:
            all_requested = db.scalars(
                select(Company).where(Company.id.in_(args.company_id))
            ).all()
            companies = [c for c in all_requested if c.status == CompanyStatus.active]
            skipped = [c for c in all_requested if c.status != CompanyStatus.active]
            if skipped:
                print(f"Skipping {len(skipped)} non-active companies:")
                for c in skipped:
                    print(f"  - {c.name} (id={c.id}, status={c.status.value})")
        elif args.tier:
            companies = db.scalars(
                select(Company)
                .where(
                    Company.data_enrichment_tier.in_(args.tier),
                    Company.status == CompanyStatus.active,
                )
            ).all()
        else:
            companies = db.scalars(
                select(Company).where(Company.status == CompanyStatus.active)
            ).all()

    if not companies:
        print("No active companies matched.")
        sys.exit(0)

    tier_map = {c.id: c.data_enrichment_tier for c in companies}
    ids = [c.id for c in companies]
    print(f"Running estimates for {len(ids)} active companies...")

    run(ids, tier_map)


if __name__ == "__main__":
    main()
