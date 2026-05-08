"""
Temporary admin endpoints — REMOVE after use.
"""
from fastapi import APIRouter, BackgroundTasks
from app.database import SessionLocal

router = APIRouter(prefix="/admin", tags=["admin"])

_status = {"running": False, "result": None}


def _run_checker():
    _status["running"] = True
    _status["result"] = None
    try:
        from app.services.status_checker import run_phase1, run_phase2_deep
        with SessionLocal() as db:
            active, unknown, _ = run_phase1(db)
        with SessionLocal() as db:
            changed, detail = run_phase2_deep(db)
        _status["result"] = {
            "phase1": {"active": active, "unknown": unknown},
            "phase2": {"changed": changed, "breakdown": detail},
        }
    except Exception as e:
        _status["result"] = {"error": str(e)}
    finally:
        _status["running"] = False


@router.get("/run-status-checker")
def run_status_checker(background_tasks: BackgroundTasks):
    if _status["running"]:
        return {"status": "already running"}
    background_tasks.add_task(_run_checker)
    return {"status": "started — check /admin/status-checker-result for progress"}


@router.get("/status-checker-result")
def status_checker_result():
    return {
        "running": _status["running"],
        "result": _status["result"],
    }
