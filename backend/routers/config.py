import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from services.config import update_config

logger = logging.getLogger(__name__)
router = APIRouter()


class ConfigRequest(BaseModel):
    warning_threshold: int
    alert_threshold: int

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.warning_threshold <= 0:
            raise ValueError("warning_threshold 必须大于 0")
        if self.alert_threshold <= self.warning_threshold:
            raise ValueError("alert_threshold 必须大于 warning_threshold")
        return self


@router.post("/config")
async def config(req: ConfigRequest):
    try:
        result = update_config(req.warning_threshold, req.alert_threshold)
    except Exception as e:
        logger.error("update_config 失败: %s", e)
        raise HTTPException(status_code=500, detail="config update failed")
    return {"status": "ok", "config": result}
