# app/api/routes/config.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, cast
from pydantic import BaseModel
from app.models.database import get_db_manager, ConfigEntry
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdate(BaseModel):
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None


@router.get("/", response_model=Dict[str, Dict[str, Any]])
async def get_all_config():
    """Get all configuration settings from database."""
    try:
        settings = get_settings()
        if not settings.database_enabled:
            raise HTTPException(
                status_code=400, detail="Database configuration is not enabled"
            )

        db_manager = get_db_manager()
        config = db_manager.get_all_config()
        return config
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.get("/{key}", response_model=ConfigResponse)
async def get_config_value(key: str):
    """Get a specific configuration value by key."""
    try:
        settings = get_settings()
        if not settings.database_enabled:
            raise HTTPException(
                status_code=400, detail="Database configuration is not enabled"
            )

        db_manager = get_db_manager()
        value = db_manager.get_config_value(key)
        if value is None:
            raise HTTPException(
                status_code=404, detail=f"Configuration key '{key}' not found"
            )

        # Get description if available
        description = None
        with db_manager.get_session() as session:
            entry = session.query(ConfigEntry).filter(ConfigEntry.key == key).first()
            if entry:
                description = cast(Optional[str], entry.description)

        return ConfigResponse(key=key, value=value, description=description)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config value for key '{key}': {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve configuration value"
        )


@router.post("/", response_model=ConfigResponse)
async def create_or_update_config(config_update: ConfigUpdate):
    """Create or update a configuration setting."""
    try:
        settings = get_settings()
        if not settings.database_enabled:
            raise HTTPException(
                status_code=400, detail="Database configuration is not enabled"
            )

        db_manager = get_db_manager()
        db_manager.set_config_value(
            key=config_update.key,
            value=config_update.value,
            description=config_update.description,
        )

        return ConfigResponse(
            key=config_update.key,
            value=config_update.value,
            description=config_update.description,
        )
    except Exception as e:
        logger.error(f"Failed to update config for key '{config_update.key}': {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.put("/{key}", response_model=ConfigResponse)
async def update_config_value(
    key: str, value: Dict[str, Any], description: Optional[str] = None
):
    """Update a configuration value by key."""
    try:
        settings = get_settings()
        if not settings.database_enabled:
            raise HTTPException(
                status_code=400, detail="Database configuration is not enabled"
            )

        db_manager = get_db_manager()
        existing_value = db_manager.get_config_value(key)
        if existing_value is None:
            raise HTTPException(
                status_code=404, detail=f"Configuration key '{key}' not found"
            )

        db_manager.set_config_value(key=key, value=value, description=description)

        return ConfigResponse(key=key, value=value, description=description)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config value for key '{key}': {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update configuration value"
        )


@router.delete("/{key}")
async def delete_config_value(key: str):
    """Delete a configuration value by key."""
    try:
        settings = get_settings()
        if not settings.database_enabled:
            raise HTTPException(
                status_code=400, detail="Database configuration is not enabled"
            )

        db_manager = get_db_manager()
        deleted = db_manager.delete_config_value(key)
        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Configuration key '{key}' not found"
            )

        return {"message": f"Configuration key '{key}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete config value for key '{key}': {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete configuration value"
        )


@router.post("/reload")
async def reload_config():
    """Reload configuration from all sources."""
    try:
        from app.core.config import get_settings

        # Clear the lru_cache to force reload
        get_settings.cache_clear()
        # Get fresh settings
        settings = get_settings()
        return {
            "message": "Configuration reloaded successfully",
            "environment": settings.environment,
        }
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload configuration")
