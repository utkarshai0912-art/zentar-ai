"""
Zentar Intelligence — Skills API Routes

Endpoints for managing and activating AI skills.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import get_current_user
from app.skills.manager import register_builtin_skills, skill_manager

logger = logging.getLogger("zentar.api.skills")
router = APIRouter(prefix="/skills", tags=["skills"])

# Ensure built-in skills are registered
register_builtin_skills()


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.get("")
async def list_skills(
    category: Optional[str] = Query(None),
    active_only: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    """List all available skills."""
    skills = skill_manager.list_skills(category=category, active_only=active_only)
    return {
        "success": True,
        "data": {
            "skills": [s.to_dict() for s in skills],
            "total": len(skills),
        },
    }


@router.get("/categories")
async def list_categories(
    user_id: str = Depends(get_current_user),
):
    """List skill categories."""
    return {"success": True, "data": skill_manager.list_categories()}


@router.get("/{skill_id}")
async def get_skill(
    skill_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get skill details."""
    skill = skill_manager.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True, "data": skill.to_dict()}


@router.post("/{skill_id}/activate")
async def activate_skill(
    skill_id: str,
    user_id: str = Depends(get_current_user),
):
    """Activate a skill."""
    success = skill_manager.activate(skill_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to activate skill")
    return {"success": True, "message": f"Skill '{skill_id}' activated"}


@router.post("/{skill_id}/deactivate")
async def deactivate_skill(
    skill_id: str,
    user_id: str = Depends(get_current_user),
):
    """Deactivate a skill."""
    success = skill_manager.deactivate(skill_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to deactivate skill")
    return {"success": True, "message": f"Skill '{skill_id}' deactivated"}


@router.get("/active/prompts")
async def get_active_prompts(
    user_id: str = Depends(get_current_user),
):
    """Get combined system prompt from active skills."""
    prompt = skill_manager.get_combined_prompt(active_only=True)
    tools = skill_manager.get_combined_tools(active_only=True)
    return {
        "success": True,
        "data": {
            "prompt": prompt,
            "tools": tools,
            "active_count": len(skill_manager.list_skills(active_only=True)),
        },
    }


@router.get("/stats")
async def skill_stats(
    user_id: str = Depends(get_current_user),
):
    """Get skill system statistics."""
    return {"success": True, "data": skill_manager.get_stats()}
