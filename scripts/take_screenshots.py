"""
Take portfolio screenshots of the FraudStream AI app.
Captures every major page at 1400x900 against production build.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3004"
OUT  = Path(__file__).parents[1] / "screenshots"
OUT.mkdir(exist_ok=True)

PAGES = [
    ("01_dashboard",      "/"),
    ("02_analytics",      "/analytics"),
    ("03_transactions",   "/transactions"),
    ("04_explainability", "/explainability"),
    ("05_drift",          "/drift"),
    ("06_infrastructure", "/infrastructure"),
]


def shot(page, name: str, path: str):
    print(f"  → {name}")
    page.goto(f"{BASE}{path}", wait_until="networkidle")
    time.sleep(2.5)   # let Recharts + queries settle
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()

    # warm up
    page.goto(BASE, wait_until="networkidle")
    time.sleep(1.5)

    print("Capturing pages...")
    for name, path in PAGES:
        try:
            shot(page, name, path)
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    browser.close()

print(f"\nDone — screenshots saved to {OUT}")
for f in sorted(OUT.glob("*.png")):
    print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")
