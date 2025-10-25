from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    TranscriptionResponse
)
from app.core.database import get_supabase_client
from app.api.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
        project: ProjectCreate,
        current_user: dict = Depends(get_current_user)
):
    """Create a new project"""
    supabase = get_supabase_client()

    new_project = supabase.table("projects").insert({
        "user_id": current_user["id"],
        "name": project.name,
        "description": project.description,
        "status": "active"
    }).execute()

    if not new_project.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

    return ProjectResponse(**new_project.data[0])


@router.get("", response_model=List[ProjectResponse])
async def get_projects(current_user: dict = Depends(get_current_user)):
    """Get all projects for the current user"""
    supabase = get_supabase_client()

    result = supabase.table("projects") \
        .select("*") \
        .eq("user_id", current_user["id"]) \
        .order("created_at", desc=True) \
        .execute()

    return [ProjectResponse(**project) for project in result.data]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
        project_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Get a specific project"""
    supabase = get_supabase_client()

    result = supabase.table("projects") \
        .select("*") \
        .eq("id", project_id) \
        .eq("user_id", current_user["id"]) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return ProjectResponse(**result.data[0])


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
        project_id: str,
        project_update: ProjectUpdate,
        current_user: dict = Depends(get_current_user)
):
    """Update a project"""
    supabase = get_supabase_client()

    # Verify project belongs to user
    existing = supabase.table("projects") \
        .select("*") \
        .eq("id", project_id) \
        .eq("user_id", current_user["id"]) \
        .execute()

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Update project
    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        return ProjectResponse(**existing.data[0])

    updated = supabase.table("projects") \
        .update(update_data) \
        .eq("id", project_id) \
        .execute()

    return ProjectResponse(**updated.data[0])


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
        project_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Delete a project"""
    supabase = get_supabase_client()

    # Verify project belongs to user
    existing = supabase.table("projects") \
        .select("*") \
        .eq("id", project_id) \
        .eq("user_id", current_user["id"]) \
        .execute()

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Delete project
    supabase.table("projects").delete().eq("id", project_id).execute()

    return None


@router.get("/{project_id}/transcriptions", response_model=List[TranscriptionResponse])
async def get_project_transcriptions(
        project_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Get all transcriptions for a project"""
    supabase = get_supabase_client()

    # Verify project belongs to user
    project = supabase.table("projects") \
        .select("*") \
        .eq("id", project_id) \
        .eq("user_id", current_user["id"]) \
        .execute()

    if not project.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get transcriptions
    result = supabase.table("transcriptions") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at", desc=True) \
        .execute()

    return [TranscriptionResponse(**t) for t in result.data]
