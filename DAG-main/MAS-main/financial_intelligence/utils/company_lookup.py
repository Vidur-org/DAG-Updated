"""Company lookup utilities

Simple CSV-backed lookup for company name -> ticker and ticker -> metadata.
Designed to be lightweight and in-memory for fast heuristic recovery.
"""
import csv
import os
import re
from typing import List, Dict

_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'company_lookup.csv')

_name_map = {}
_ticker_map = {}
_loaded = False


def _load():
    global _loaded
    if _loaded:
        return

    try:
        with open(os.path.abspath(_PATH), newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['name'].strip()
                ticker = row['ticker'].strip()
                country = row.get('country', '').strip()
                _name_map[name.lower()] = {'name': name, 'ticker': ticker, 'country': country}
                _ticker_map[ticker.upper()] = {'name': name, 'ticker': ticker, 'country': country}
    except FileNotFoundError:
        # No file present — keep maps empty
        pass

    _loaded = True


def lookup_by_name(name: str):
    _load()
    return _name_map.get(name.lower())


def lookup_by_ticker(ticker: str):
    _load()
    return _ticker_map.get(ticker.upper())


def find_companies_in_text(text: str) -> List[Dict]:
    """Find companies mentioned in text using name matching and ticker scanning.

    Returns a list of dicts: { 'name', 'ticker', 'country' }
    """
    _load()
    found = []
    txt = text or ""

    # 1) Explicit ticker mentions like RELIANCE.NS or AAPL
    for tk in re.findall(r"\b[A-Z0-9]{2,30}\.[A-Z]{1,4}\b", txt):
        meta = lookup_by_ticker(tk)
        if meta and meta not in found:
            found.append(meta)
        else:
            # We still append a minimal record if ticker not in CSV
            candidate = {'name': tk.split('.')[0].title(), 'ticker': tk, 'country': ''}
            if candidate not in found:
                found.append(candidate)

    # 2) Name-based matches (longer names first to avoid substring collisions)
    names = sorted(_name_map.keys(), key=lambda x: -len(x))
    lowered = txt.lower()
    for name in names:
        if name in lowered:
            meta = _name_map[name]
            if meta not in found:
                found.append(meta)

    # 3) Capitalized candidate fallback (only if nothing found yet)
    if not found:
        caps = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', txt)
        for c in caps:
            # avoid small words
            if len(c) < 3:
                continue
            # try lookup by name
            m = lookup_by_name(c)
            if m and m not in found:
                found.append(m)

    return found
