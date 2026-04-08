"""Plugin management API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

router = APIRouter(prefix="/plugins", tags=["plugins"])
logger = logging.getLogger(__name__)


class PluginInfoResponse(BaseModel):
    """Plugin information response."""

    name: str
    version: str
    description: str
    author: str
    enabled: bool
    hooks: list[str]


class PluginListResponse(BaseModel):
    """Response for listing all plugins."""

    plugins: list[PluginInfoResponse]
    total: int


class PluginActionResponse(BaseModel):
    """Response for plugin enable/disable actions."""

    name: str
    enabled: bool
    message: str


class PluginStatsRequest(BaseModel):
    """Request for computing plugin stats."""

    content: str


class PluginStatsResponse(BaseModel):
    """Response with computed stats from plugins."""

    word_count: int | None = None
    character_count: int | None = None
    line_count: int | None = None
    reading_time_minutes: float | None = None


@router.get("", response_model=PluginListResponse)
async def list_plugins(request: Request) -> PluginListResponse:
    """List all loaded plugins.

    Returns:
        List of all plugins with their status
    """
    plugin_manager = getattr(request.app.state, "plugin_manager", None)
    if plugin_manager is None:
        return PluginListResponse(plugins=[], total=0)

    plugins = plugin_manager.list_plugins()
    return PluginListResponse(
        plugins=[
            PluginInfoResponse(
                name=p.name,
                version=p.version,
                description=p.description,
                author=p.author,
                enabled=p.enabled,
                hooks=[h.value for h in p.hooks],
            )
            for p in plugins
        ],
        total=len(plugins),
    )


@router.get("/{name}", response_model=PluginInfoResponse)
async def get_plugin(request: Request, name: str) -> PluginInfoResponse:
    """Get information about a specific plugin.

    Args:
        name: Plugin name

    Returns:
        Plugin information
    """
    plugin_manager = getattr(request.app.state, "plugin_manager", None)
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    plugin = plugin_manager.get_plugin(name)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{name}' not found",
        )

    info = plugin.info
    return PluginInfoResponse(
        name=info.name,
        version=info.version,
        description=info.description,
        author=info.author,
        enabled=info.enabled,
        hooks=[h.value for h in info.hooks],
    )


@router.post("/{name}/enable", response_model=PluginActionResponse)
async def enable_plugin(request: Request, name: str) -> PluginActionResponse:
    """Enable a plugin.

    Args:
        name: Plugin name

    Returns:
        Action result
    """
    plugin_manager = getattr(request.app.state, "plugin_manager", None)
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    plugin = plugin_manager.get_plugin(name)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{name}' not found",
        )

    success = await plugin_manager.enable_plugin(name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable plugin '{name}'",
        )

    logger.info(f"Plugin enabled via API: {name}")
    return PluginActionResponse(
        name=name,
        enabled=True,
        message=f"Plugin '{name}' enabled successfully",
    )


@router.post("/{name}/disable", response_model=PluginActionResponse)
async def disable_plugin(request: Request, name: str) -> PluginActionResponse:
    """Disable a plugin.

    Args:
        name: Plugin name

    Returns:
        Action result
    """
    plugin_manager = getattr(request.app.state, "plugin_manager", None)
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin system not initialized",
        )

    plugin = plugin_manager.get_plugin(name)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{name}' not found",
        )

    success = await plugin_manager.disable_plugin(name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable plugin '{name}'",
        )

    logger.info(f"Plugin disabled via API: {name}")
    return PluginActionResponse(
        name=name,
        enabled=False,
        message=f"Plugin '{name}' disabled successfully",
    )


@router.post("/compute-stats", response_model=PluginStatsResponse)
async def compute_stats(
    request: Request, body: PluginStatsRequest
) -> PluginStatsResponse:
    """Compute stats for content using enabled plugins.

    This endpoint allows testing the METADATA_COMPUTE hook.

    Args:
        body: Request with content to analyze

    Returns:
        Computed stats from plugins
    """
    plugin_manager = getattr(request.app.state, "plugin_manager", None)
    if plugin_manager is None:
        return PluginStatsResponse()

    from ..plugins.base import PluginHook

    data = {"content": body.content, "metadata": {}}
    result = await plugin_manager.execute_hook(PluginHook.METADATA_COMPUTE, data)

    metadata = result.get("metadata", {})
    return PluginStatsResponse(
        word_count=metadata.get("word_count"),
        character_count=metadata.get("character_count"),
        line_count=metadata.get("line_count"),
        reading_time_minutes=metadata.get("reading_time_minutes"),
    )
