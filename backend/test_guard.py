import sys; sys.path.insert(0, ".")
from app.config import settings
from sqlalchemy import create_engine, text

e = create_engine(settings.database_url)
with e.connect() as c:
    row = c.execute(text(
        "SELECT id, name, status FROM companies WHERE status = 'Acquired' LIMIT 1"
    )).fetchone()
    print(f"Testing guard on: id={row[0]}, name={row[1]}, status={row[2]}")
    acquired_id = row[0]

from app.database import SessionLocal
from app.services.spend_estimator import estimate

try:
    with SessionLocal() as db:
        estimate(acquired_id, db)
    print("ERROR: should have raised")
except ValueError as ex:
    print(f"Guard raised correctly: {ex}")

# Also test CLI skip reporting
print()
print("Testing CLI skip reporting...")
import subprocess, sys
result = subprocess.run(
    [sys.executable, "-m", "app.services.run_estimates", "--company-id", "3", str(acquired_id)],
    capture_output=True, text=True
)
print(result.stdout)
if result.stderr:
    print("stderr:", result.stderr)
