from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()

class CreateExternalJobRequest(BaseModel):
    connector: str = Field(min_length=1, max_length=64)
    operation: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)

class ExternalJobResponse(BaseModel):
    job_id: str
    status: str

@router.post("/integration/external-jobs", response_model=ExternalJobResponse)
async def create_external_job(request: Request, body: CreateExternalJobRequest):
    return ExternalJobResponse(job_id="JOB-1", status="CREATED")
