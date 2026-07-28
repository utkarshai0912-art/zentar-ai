"""
Zentar Intelligence — Marketplace API Routes

Plugin and skill marketplace endpoints for browsing and installing
community extensions.
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import get_current_user
from app.agents.marketplace import marketplace_reader

logger = logging.getLogger("zentar.api.marketplace")
router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class MarketplaceItem(BaseModel):
    id: str
    name: str
    description: str
    type: str  # plugin, skill
    author: str
    version: str
    category: str
    downloads: int = 0
    rating: float = 0.0
    icon: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None


# In-memory marketplace catalog
MARKETPLACE_ITEMS: List[MarketplaceItem] = []


def init_marketplace():
    """Initialize the marketplace with default items."""
    global MARKETPLACE_ITEMS
    if MARKETPLACE_ITEMS:
        return

    MARKETPLACE_ITEMS = [
        MarketplaceItem(
            id="plugin-web-search",
            name="Web Search",
            description="Adds web search capability to your AI assistant using DuckDuckGo or SerpAPI",
            type="plugin",
            author="Zentar Labs",
            version="1.0.0",
            category="tools",
            downloads=1200,
            rating=4.5,
            icon="search",
            license="MIT",
        ),
        MarketplaceItem(
            id="plugin-code-executor",
            name="Code Executor",
            description="Sandboxed Python code execution for data analysis and automation",
            type="plugin",
            author="Zentar Labs",
            version="1.1.0",
            category="coding",
            downloads=890,
            rating=4.3,
            icon="code",
            license="MIT",
        ),
        MarketplaceItem(
            id="plugin-weather",
            name="Weather Assistant",
            description="Get current weather and forecasts for any location",
            type="plugin",
            author="Community",
            version="1.0.0",
            category="tools",
            downloads=650,
            rating=4.0,
            icon="cloud",
            license="Apache 2.0",
        ),
        MarketplaceItem(
            id="plugin-pdf-reader",
            name="PDF Reader",
            description="Read and extract text from PDF documents",
            type="plugin",
            author="Zentar Labs",
            version="1.0.0",
            category="document",
            downloads=450,
            rating=3.8,
            icon="picture_as_pdf",
            license="MIT",
        ),
        MarketplaceItem(
            id="skill-data-viz",
            name="Data Visualization",
            description="Creates charts and graphs from your data using matplotlib",
            type="skill",
            author="Zentar Labs",
            version="1.0.0",
            category="data",
            downloads=320,
            rating=4.2,
            icon="bar_chart",
            license="MIT",
        ),
        MarketplaceItem(
            id="skill-email-composer",
            name="Email Composer",
            description="Drafts professional emails based on brief instructions",
            type="skill",
            author="Community",
            version="1.0.0",
            category="writing",
            downloads=280,
            rating=4.1,
            icon="email",
            license="MIT",
        ),
        MarketplaceItem(
            id="plugin-sql-helper",
            name="SQL Query Helper",
            description="Write and optimize SQL queries with AI assistance",
            type="plugin",
            author="Zentar Labs",
            version="1.0.0",
            category="data",
            downloads=210,
            rating=4.6,
            icon="storage",
            license="MIT",
        ),
        MarketplaceItem(
            id="skill-translator-pro",
            name="Translator Pro",
            description="Advanced translation with context awareness and industry terminology",
            type="skill",
            author="Community",
            version="1.0.0",
            category="writing",
            downloads=190,
            rating=3.9,
            icon="translate",
            license="Apache 2.0",
        ),
    ]


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.get("/items")
async def list_marketplace(
    category: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None, alias="type"),
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
):
    """Browse marketplace items."""
    init_marketplace()
    items = MARKETPLACE_ITEMS.copy()

    if category:
        items = [i for i in items if i.category == category]
    if item_type:
        items = [i for i in items if i.type == item_type]
    if query:
        q = query.lower()
        items = [i for i in items if q in i.name.lower() or q in i.description.lower()]

    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start:start + page_size]

    return {
        "success": True,
        "data": {
            "items": [i.dict() for i in page_items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/categories")
async def list_marketplace_categories(
    user_id: str = Depends(get_current_user),
):
    """List available categories."""
    init_marketplace()
    categories = set()
    type_filters = set()
    for item in MARKETPLACE_ITEMS:
        categories.add(item.category)
        type_filters.add(item.type)
    return {
        "success": True,
        "data": {
            "categories": sorted(categories),
            "types": sorted(type_filters),
        },
    }


@router.get("/items/{item_id}")
async def get_marketplace_item(
    item_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get marketplace item details."""
    init_marketplace()
    for item in MARKETPLACE_ITEMS:
        if item.id == item_id:
            return {"success": True, "data": item.dict()}
    raise HTTPException(status_code=404, detail="Item not found")


# ──────────────────────────────────────────
# WSHobson Agent Marketplace Routes
# ──────────────────────────────────────────

@router.get("/wshobson/agents")
async def list_wshobson_agents(
    plugin: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    model_tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user_id: str = Depends(get_current_user),
):
    """List agents from the wshobson/agents marketplace."""
    agents = marketplace_reader.list_agents(
        plugin=plugin,
        category=category,
        model_tier=model_tier,
        search=search,
        limit=limit,
    )
    return {
        "success": True,
        "data": {
            "agents": [a.to_dict() for a in agents],
            "total": len(agents),
        },
    }


@router.get("/wshobson/agents/{agent_id}")
async def get_wshobson_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get a specific wshobson agent with full system prompt."""
    agent = marketplace_reader.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "data": agent.to_dict()}


@router.post("/wshobson/agents/{agent_id}/install")
async def install_wshobson_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user),
):
    """Install a wshobson agent as a custom agent."""
    success, message = marketplace_reader.install_agent(agent_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@router.get("/wshobson/plugins")
async def list_wshobson_plugins(
    user_id: str = Depends(get_current_user),
):
    """List all plugins in the wshobson marketplace."""
    return {
        "success": True,
        "data": {
            "plugins": marketplace_reader.list_plugins(),
        },
    }


@router.get("/wshobson/categories")
async def list_wshobson_categories(
    user_id: str = Depends(get_current_user),
):
    """List agent categories with counts."""
    return {
        "success": True,
        "data": {
            "categories": marketplace_reader.list_categories(),
        },
    }


@router.get("/wshobson/stats")
async def get_wshobson_stats(
    user_id: str = Depends(get_current_user),
):
    """Get marketplace statistics."""
    return {"success": True, "data": marketplace_reader.get_stats()}
