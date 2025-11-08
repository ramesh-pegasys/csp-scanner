# app/api/routes/config.py
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from app.models.database import get_db_manager
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])


class ConfigUpdate(BaseModel):
    """Configuration update model - accepts any valid Settings fields."""

    config: Dict[str, Any]
    description: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "config": {
                        "debug": True,
                        "max_concurrent_extractors": 20,
                        "batch_size": 100,
                        "enabled_providers": ["aws", "azure", "gcp"],
                        "transport": {
                            "type": "http",
                            "http_endpoint_url": "https://scanner.example.com/api/artifacts",
                            "timeout_seconds": 60,
                            "max_retries": 5,
                        },
                    },
                    "description": "Updated configuration for multi-cloud support",
                },
                {
                    "config": {
                        "debug": False,
                        "environment": "production",
                        "max_concurrent_extractors": 50,
                        "aws_accounts": [
                            {
                                "account_id": "123456789012",
                                "regions": ["us-east-1", "us-west-2"],
                            }
                        ],
                    },
                    "description": "Production configuration with increased concurrency",
                },
            ]
        }
    }


class ConfigResponse(BaseModel):
    """Configuration response model."""

    config: Dict[str, Any]
    version: Optional[int] = None
    is_active: bool
    applied: bool
    message: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "config": {
                        "app_name": "Cloud Artifact Extractor",
                        "environment": "development",
                        "debug": True,
                        "enabled_providers": ["aws", "gcp"],
                        "max_concurrent_extractors": 10,
                        "batch_size": 100,
                        "transport_type": "http",
                        "http_endpoint_url": "http://localhost:8000",
                        "allow_insecure_ssl": True,
                    },
                    "version": 5,
                    "is_active": True,
                    "applied": True,
                    "message": "Configuration updated and applied successfully",
                    "created_at": "2025-11-04T10:30:00Z",
                    "updated_at": "2025-11-04T10:30:00Z",
                }
            ]
        }
    }


class ConfigVersionInfo(BaseModel):
    """Configuration version metadata."""

    id: int
    version: int
    is_active: bool
    description: Optional[str] = None
    created_at: str
    updated_at: str
    config: Dict[str, Any]


@router.get("/", response_model=ConfigResponse)
async def get_current_config():
    """Get the currently active configuration."""
    try:
        # Clear cache to ensure we get the latest config from database
        get_settings.cache_clear()
        settings = get_settings()

        # Convert settings to dict, excluding internal fields
        config_dict = settings.model_dump(exclude={"model_config"}, exclude_none=False)

        # Get version info if database enabled
        version = None
        created_at = None
        updated_at = None
        if settings.database_enabled:
            db_manager = get_db_manager()
            versions = db_manager.list_config_versions(limit=1)
            if versions:
                active_version = versions[0]
                version = active_version["version"]
                created_at = active_version["created_at"]
                updated_at = active_version["updated_at"]

        return ConfigResponse(
            config=config_dict,
            version=version,
            is_active=True,
            applied=True,
            message="Current active configuration",
            created_at=created_at,
            updated_at=updated_at,
        )
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.put("/", response_model=ConfigResponse)
async def update_config(request: Request, config_update: ConfigUpdate):
    """
    Create a new configuration version and set it as active.

    This will:
    1. Create a new configuration version in the database
    2. Set it as the active configuration (deactivating previous versions)
    3. Apply it to the running server by reloading settings
    4. Reinitialize components that depend on configuration
    """
    try:
        settings = get_settings()

        if not settings.database_enabled:
            raise HTTPException(
                status_code=400,
                detail="Database must be enabled to use versioned configuration",
            )

        # Create new configuration version
        db_manager = get_db_manager()
        version = db_manager.create_config_version(
            config=config_update.config,
            description=config_update.description,
            set_active=True,
        )
        logger.info(f"Created configuration version {version} and set as active")

        # Clear the settings cache to force reload from active config
        get_settings.cache_clear()

        # Reload settings with new config
        new_settings = get_settings()

        # Reinitialize components if they exist in app state
        if hasattr(request.app.state, "orchestrator"):
            orchestrator = request.app.state.orchestrator
            orchestrator.max_concurrent = new_settings.max_concurrent_extractors
            logger.info("Orchestrator configuration updated")

        if hasattr(request.app.state, "registry"):
            logger.info("Registry aware of configuration change")

        # Get version info
        versions = db_manager.list_config_versions(limit=1)
        version_info = versions[0] if versions else {}

        logger.info(f"Configuration version {version} applied successfully")

        return ConfigResponse(
            config=config_update.config,
            version=version,
            is_active=True,
            applied=True,
            message=f"Configuration version {version} created and applied successfully",
            created_at=version_info.get("created_at"),
            updated_at=version_info.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update configuration: {str(e)}"
        )


@router.patch("/", response_model=ConfigResponse)
async def patch_config(request: Request, config_update: ConfigUpdate):
    """
    Partially update the server configuration by creating a new version.

    This merges the provided configuration fields with the active config,
    creates a new version, and applies it to the running server.
    """
    try:
        settings = get_settings()

        if not settings.database_enabled:
            raise HTTPException(
                status_code=400,
                detail="Database must be enabled to use versioned configuration",
            )

        # Get current active config
        db_manager = get_db_manager()
        current_config = db_manager.get_active_config() or {}

        logger.info(f"Current active config has {len(current_config)} keys")
        logger.info(f"Patch update contains: {list(config_update.config.keys())}")

        # Merge with new config (new values override existing)
        merged_config = {**current_config, **config_update.config}

        logger.info(f"Merged config has {len(merged_config)} keys")
        logger.info(f"Debug value after merge: {merged_config.get('debug')}")

        # Create new version with merged config
        version = db_manager.create_config_version(
            config=merged_config,
            description=config_update.description or "Partial configuration update",
            set_active=True,
        )
        logger.info(f"Created configuration version {version} with merged config")

        # Clear the settings cache to force reload
        get_settings.cache_clear()

        # Reload settings with merged config
        new_settings = get_settings()

        # Reinitialize components if they exist in app state
        if hasattr(request.app.state, "orchestrator"):
            orchestrator = request.app.state.orchestrator
            orchestrator.max_concurrent = new_settings.max_concurrent_extractors
            logger.info("Orchestrator configuration updated")

        # Get version info
        versions = db_manager.list_config_versions(limit=1)
        version_info = versions[0] if versions else {}

        logger.info(f"Configuration version {version} applied successfully")
        logger.info(
            f"Returning version {version} with debug={merged_config.get('debug')}"
        )
        logger.info(
            f"Version info from DB: version={version_info.get('version')}, is_active={version_info.get('is_active')}"
        )

        return ConfigResponse(
            config=merged_config,
            version=version,
            is_active=True,
            applied=True,
            message=f"Configuration version {version} created with partial update and applied",
            created_at=version_info.get("created_at"),
            updated_at=version_info.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to patch config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to patch configuration: {str(e)}"
        )


@router.post("/reload", response_model=ConfigResponse)
async def reload_config(request: Request):
    """
    Reload the active configuration and apply to running server.

    This will reload the currently active configuration from the database
    and apply it to the running server.
    """
    try:
        # Clear the lru_cache to force reload
        get_settings.cache_clear()

        # Get fresh settings (will load from active config in DB if enabled)
        settings = get_settings()

        # Reinitialize components
        if hasattr(request.app.state, "orchestrator"):
            orchestrator = request.app.state.orchestrator
            orchestrator.max_concurrent = settings.max_concurrent_extractors
            logger.info("Orchestrator reinitialized with reloaded config")

        config_dict = settings.model_dump(exclude={"model_config"}, exclude_none=False)

        # Get version info if database enabled
        version = None
        created_at = None
        updated_at = None
        if settings.database_enabled:
            db_manager = get_db_manager()
            versions = db_manager.list_config_versions(limit=1)
            if versions:
                active_version = versions[0]
                version = active_version["version"]
                created_at = active_version["created_at"]
                updated_at = active_version["updated_at"]

        logger.info("Configuration reloaded from active version")

        return ConfigResponse(
            config=config_dict,
            version=version,
            is_active=True,
            applied=True,
            message="Active configuration reloaded and applied successfully",
            created_at=created_at,
            updated_at=updated_at,
        )
    except Exception as e:
        logger.error(f"Failed to reload config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to reload configuration: {str(e)}"
        )


@router.get("/versions", response_model=List[ConfigVersionInfo])
async def list_config_versions(limit: int = 50):
    """
    List all configuration versions with metadata.

    Returns versions in descending order (newest first).
    """
    try:
        settings = get_settings()

        if not settings.database_enabled:
            raise HTTPException(
                status_code=400,
                detail="Database must be enabled to use versioned configuration",
            )

        db_manager = get_db_manager()
        versions = db_manager.list_config_versions(limit=limit)

        return versions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list config versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list configuration versions: {str(e)}"
        )


@router.get("/versions/{version}", response_model=ConfigVersionInfo)
async def get_config_version(version: int):
    """Get a specific configuration version."""
    try:
        settings = get_settings()

        if not settings.database_enabled:
            raise HTTPException(
                status_code=400,
                detail="Database must be enabled to use versioned configuration",
            )

        db_manager = get_db_manager()
        versions = db_manager.list_config_versions(limit=1000)

        # Find the requested version
        version_data = next((v for v in versions if v["version"] == version), None)

        if not version_data:
            raise HTTPException(
                status_code=404, detail=f"Configuration version {version} not found"
            )

        return version_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config version {version}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get configuration version: {str(e)}"
        )


@router.post("/versions/{version}/activate", response_model=ConfigResponse)
async def activate_config_version(request: Request, version: int):
    """
    Activate a specific configuration version.

    This will set the specified version as active, deactivate all others,
    and apply the configuration to the running server.
    """
    try:
        settings = get_settings()

        if not settings.database_enabled:
            raise HTTPException(
                status_code=400,
                detail="Database must be enabled to use versioned configuration",
            )

        db_manager = get_db_manager()
        success = db_manager.activate_config_version(version)

        if not success:
            raise HTTPException(
                status_code=404, detail=f"Configuration version {version} not found"
            )

        logger.info(f"Activated configuration version {version}")

        # Clear the settings cache to force reload
        get_settings.cache_clear()

        # Reload settings with activated version
        new_settings = get_settings()

        # Reinitialize components
        if hasattr(request.app.state, "orchestrator"):
            orchestrator = request.app.state.orchestrator
            orchestrator.max_concurrent = new_settings.max_concurrent_extractors
            logger.info("Orchestrator reinitialized with activated version")

        # Get the activated version info
        config = db_manager.get_config_version(version)
        versions = db_manager.list_config_versions(limit=1)
        version_info = versions[0] if versions else {}

        return ConfigResponse(
            config=config or {},
            version=version,
            is_active=True,
            applied=True,
            message=f"Configuration version {version} activated and applied successfully",
            created_at=version_info.get("created_at"),
            updated_at=version_info.get("updated_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate config version {version}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate configuration version: {str(e)}",
        )


@router.delete("/versions/{version}")
async def delete_config_version(version: int):
    """
    Delete a specific configuration version.

    Cannot delete the currently active version.
    """
    try:
        settings = get_settings()

        if not settings.database_enabled:
            raise HTTPException(
                status_code=400,
                detail="Database must be enabled to use versioned configuration",
            )

        db_manager = get_db_manager()
        success = db_manager.delete_config_version(version)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete version {version}: either not found or is currently active",
            )

        logger.info(f"Deleted configuration version {version}")

        return {"message": f"Configuration version {version} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete config version {version}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete configuration version: {str(e)}"
        )
