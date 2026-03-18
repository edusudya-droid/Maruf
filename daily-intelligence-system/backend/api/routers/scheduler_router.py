"""Scheduler API — vazifalarni ko'rish va qo'lda ishga tushirish."""
from fastapi import APIRouter, Depends, HTTPException
from backend.api.dependencies import verify_admin

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

JOB_MAP = {
    "parse_sources": "scheduler.jobs.job_parse_sources",
    "process_articles": "scheduler.jobs.job_process_articles",
    "detect_events": "scheduler.jobs.job_detect_events",
    "update_source_scores": "scheduler.jobs.job_update_source_scores",
    "morning_brief": "scheduler.jobs.job_generate_morning_brief",
    "midday_brief": "scheduler.jobs.job_generate_midday_brief",
    "evening_brief": "scheduler.jobs.job_generate_evening_brief",
}


@router.get("/jobs")
async def list_jobs(_: None = Depends(verify_admin)):
    return {"jobs": list(JOB_MAP.keys())}


@router.post("/run/{job_name}")
async def run_job(job_name: str, _: None = Depends(verify_admin)):
    if job_name not in JOB_MAP:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_name}")

    import importlib
    module_path, func_name = JOB_MAP[job_name].rsplit(".", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)

    import asyncio
    asyncio.create_task(func())
    return {"message": f"Job '{job_name}' started"}
