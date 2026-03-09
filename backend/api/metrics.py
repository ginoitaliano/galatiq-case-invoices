# backend/api/metrics.py
from fastapi import APIRouter
from services import metrics_service

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    return metrics_service.get_metrics()