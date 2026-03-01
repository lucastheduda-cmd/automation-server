import uuid
import importlib
import traceback
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

app = FastAPI(title="Automation Server")

API_KEY = os.environ.get("API_KEY", "changeme")
api_key_header = APIKeyHeader(name="X-API-Key")

# In-memory job store (resets on restart)
jobs: dict = {}


def verify_key(key: str = Depends(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return key


class JobRequest(BaseModel):
    job: str
    params: dict = {}


def run_job(job_id: str, job_name: str, params: dict):
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
    try:
        module = importlib.import_module(f"jobs.{job_name}")
        result = module.run(**params)
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = str(result)
    except ModuleNotFoundError:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = f"No job named '{job_name}' found in jobs/ folder."
    except Exception:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = traceback.format_exc()
    jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


@app.get("/")
def health():
    return {"status": "ok", "jobs_in_memory": len(jobs)}


@app.post("/jobs", dependencies=[Depends(verify_key)])
async def create_job(req: JobRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "job": req.job,
        "params": req.params,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }
    background_tasks.add_task(run_job, job_id, req.job, req.params)
    return jobs[job_id]


@app.get("/jobs", dependencies=[Depends(verify_key)])
def list_jobs():
    return sorted(jobs.values(), key=lambda j: j["created_at"], reverse=True)


@app.get("/jobs/{job_id}", dependencies=[Depends(verify_key)])
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.delete("/jobs/{job_id}", dependencies=[Depends(verify_key)])
def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    del jobs[job_id]
    return {"deleted": job_id}
