"""
Company status enrichment — two phases:

  Phase 1  yfinance batch check: marks companies Active or Unknown
  Phase 2  yfinance deep check: enriches Unknown companies using
           .info fields (quoteType, delistingDate, longName),
           Russian/sanctioned ticker detection, and name pattern matching

CLI usage (run from backend/):
    python -m app.services.status_checker --phase 1
    python -m app.services.status_checker --phase 2
    python -m app.services.status_checker          # runs both
"""
import html as _html
import re
import sys
import time
from pathlib import Path

import yfinance as yf
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, CompanyStatus

BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Phase 1 — yfinance batch download
# ---------------------------------------------------------------------------

def _check_batch(tickers: list[str]) -> dict[str, bool]:
    if not tickers:
        return {}
    try:
        import pandas as pd
        raw = yf.download(tickers, period="5d", auto_adjust=True, progress=False, threads=True)

        if len(tickers) == 1:
            series = raw.get("Close", pd.Series())
            return {tickers[0]: not series.dropna().empty}

        close_df = raw.get("Close", pd.DataFrame())
        results = {}
        for t in tickers:
            try:
                results[t] = t in close_df.columns and not close_df[t].dropna().empty
            except Exception:
                results[t] = False
        return results
    except Exception as e:
        print(f"    Batch error: {e}", flush=True)
        return {t: False for t in tickers}


def run_phase1(db: Session) -> tuple[int, int, list[str]]:
    companies = db.scalars(select(Company).where(Company.ticker.isnot(None))).all()
    tickers = [c.ticker.upper() for c in companies]

    all_results: dict[str, bool] = {}
    total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  [yfinance] Batch {batch_num}/{total_batches} — {len(batch)} tickers ...", flush=True)
        all_results.update(_check_batch(batch))
        time.sleep(1)

    active = unknown = 0
    unknown_list: list[str] = []

    for company in companies:
        t = company.ticker.upper()
        if all_results.get(t, False):
            company.status = CompanyStatus.active
            active += 1
        else:
            company.status = CompanyStatus.unknown
            unknown += 1
            unknown_list.append(f"{company.ticker} | {company.name}")

    db.commit()
    return active, unknown, unknown_list


# ---------------------------------------------------------------------------
# Phase 2 — deep enrichment of Unknown companies
# ---------------------------------------------------------------------------

# Russian / sanctioned exchange suffixes (Moscow Exchange)
_SANCTIONED_SUFFIXES = (".ME", ".MM", ".MSE")

# Regex patterns on company names
_ACQUIRED_BY_RE = re.compile(r"\((.+?)\s+acquisition\)", re.IGNORECASE)
_MERGED_WITH_RE = re.compile(r"\bmerged?\s+(?:with|into)\s+([A-Za-z0-9 &]+)", re.IGNORECASE)
_PRIVATE_RE = re.compile(r"\b(private|privately\s+held|taken\s+private|LLC\b|Ltd\.?\b)", re.IGNORECASE)
_SLASH_TICKER_RE = re.compile(r"[A-Z0-9]+/[A-Z0-9]+")


def _is_sanctioned(ticker: str) -> bool:
    return any(ticker.upper().endswith(s) for s in _SANCTIONED_SUFFIXES)


def _match_name(name: str, ticker: str) -> dict | None:
    """Return status dict if company name/ticker contains a clear signal."""
    # Invalid ticker format (e.g. PAA/PAGP, DKL/DK)
    if _SLASH_TICKER_RE.fullmatch(ticker.upper()):
        return {
            "status": CompanyStatus.unknown,
            "notes": f"Non-standard ticker format (combined listing): {ticker}",
        }

    # Explicit "XYZ acquisition" in parentheses
    m = _ACQUIRED_BY_RE.search(name)
    if m:
        acquirer = m.group(1).strip()
        return {
            "status": CompanyStatus.acquired,
            "acquired_by": acquirer,
            "notes": f"Acquired by {acquirer} (flagged in company name)",
        }

    # "merged with / merged into"
    m = _MERGED_WITH_RE.search(name)
    if m:
        partner = m.group(1).strip()
        return {
            "status": CompanyStatus.merged,
            "acquired_by": partner,
            "notes": f"Merged with {partner} (flagged in company name)",
        }

    # Private / LLC / Ltd — not publicly traded
    if _PRIVATE_RE.search(name):
        return {
            "status": CompanyStatus.delisted,
            "notes": "Private or non-public entity (flagged in company name)",
        }

    return None


def _clean_text(s: str | None) -> str | None:
    """Fix UTF-8-decoded-as-Latin-1 mojibake and HTML entities in yfinance text fields."""
    if not s:
        return s
    try:
        s = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return _html.unescape(s).strip()


def _yf_info(ticker: str) -> dict:
    """Fetch yfinance .info safely, returning {} on any failure."""
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


def run_phase2_deep(db: Session) -> tuple[int, dict[str, str]]:
    """
    Enrich Unknown companies with deeper yfinance data + name matching.
    Returns (count_changed, {ticker: new_status}).
    """
    unknowns = db.scalars(
        select(Company).where(Company.status == CompanyStatus.unknown)
    ).all()

    print(f"  [deep] Enriching {len(unknowns)} Unknown companies ...", flush=True)
    changes: dict[str, str] = {}

    for i, company in enumerate(unknowns, 1):
        ticker = (company.ticker or "").strip()

        # 1. Sanctioned / Russian exchange
        if _is_sanctioned(ticker):
            company.status = CompanyStatus.sanctioned
            company.acquisition_notes = (
                "Trading restricted — Moscow Exchange (Western sanctions post-2022)"
            )
            changes[ticker] = "Sanctioned"
            print(f"  [{i}/{len(unknowns)}] {ticker}: Sanctioned", flush=True)
            continue

        # 2. Name / ticker pattern matching
        name_match = _match_name(company.name, ticker)
        if name_match:
            company.status = name_match["status"]
            company.acquired_by = name_match.get("acquired_by")
            company.acquisition_notes = name_match.get("notes")
            label = company.status.value
            changes[ticker] = label
            if label != "Unknown":
                print(f"  [{i}/{len(unknowns)}] {ticker}: {label} (name match)", flush=True)
            continue

        # 3. Deep yfinance .info
        print(f"  [{i}/{len(unknowns)}] {ticker}: fetching .info ...", flush=True)
        info = _yf_info(ticker)
        qt = (info.get("quoteType") or "").upper()
        delisting = info.get("delistingDate")
        long_name = _clean_text(info.get("longName") or "") or ""
        exchange = _clean_text(info.get("exchange") or "") or ""

        if qt in ("MUTUALFUND", "ETF", "INDEX", "CURRENCY", "FUTURE"):
            company.status = CompanyStatus.non_equity
            company.acquisition_notes = f"Not an equity instrument: {qt}"
            changes[ticker] = "Non-Equity"
            print(f"  [{i}/{len(unknowns)}] {ticker}: Non-Equity ({qt})", flush=True)

        elif delisting:
            company.status = CompanyStatus.delisted
            company.acquisition_notes = f"Delisted {delisting}"
            changes[ticker] = "Delisted"
            print(f"  [{i}/{len(unknowns)}] {ticker}: Delisted {delisting}", flush=True)

        else:
            # Still no signal — annotate with whatever info we got
            notes_parts = []
            if long_name and long_name.lower() != company.name.lower():
                notes_parts.append(f"yfinance name: {long_name}")
            if exchange:
                notes_parts.append(f"exchange: {exchange}")
            if qt:
                notes_parts.append(f"quoteType: {qt}")
            if notes_parts:
                company.acquisition_notes = "; ".join(notes_parts)
            changes[ticker] = "Unknown"

        time.sleep(0.2)

    db.commit()
    return len([v for v in changes.values() if v != "Unknown"]), changes


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Company status enrichment")
    parser.add_argument(
        "--phase", type=int, choices=[1, 2], default=0,
        help="1=yfinance batch, 2=deep enrichment, omit=both",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.phase in (1, 0):
            print("\n=== Phase 1: yfinance batch check ===", flush=True)
            active, unknown, unknown_list = run_phase1(db)
            print(f"\nResults: {active} Active, {unknown} Unknown\n")
            for line in unknown_list:
                print(f"  {line}")

        if args.phase in (2, 0):
            print("\n=== Phase 2: deep enrichment ===", flush=True)
            changed, detail = run_phase2_deep(db)
            print(f"\nChanged {changed} companies from Unknown\n")

        # Final summary
        rows = db.execute(
            select(Company.status, func.count(Company.id).label("n"))
            .group_by(Company.status)
        ).all()
        print("\nFinal status breakdown:")
        for status, n in sorted(rows, key=lambda r: r[1], reverse=True):
            print(f"  {str(status):14s} {n}")


if __name__ == "__main__":
    main()
