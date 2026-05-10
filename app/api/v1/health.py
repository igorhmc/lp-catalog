from fastapi import APIRouter
import time
from utils.uptime import get_uptime_seconds, get_uptime_human

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime": get_uptime_human(),
        "uptime_seconds": get_uptime_seconds()
    }