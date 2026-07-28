"""
Zentar Intelligence — Voice API Routes

Endpoints for voice assistant interaction.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.voice_service import voice_service

logger = logging.getLogger("zentar.api.voice")
router = APIRouter(prefix="/voice", tags=["voice"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = 1.0


class CommandResponse(BaseModel):
    success: bool
    transcription: Optional[str] = None
    command: Optional[dict] = None
    error: Optional[str] = None


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Transcribe an audio file to text."""
    audio_data = await file.read()
    format = file.filename.split(".")[-1] if file.filename else "wav"

    text = await voice_service.transcribe_audio(audio_data, format=format)
    return {
        "success": True,
        "data": {"transcription": text, "audio_size": len(audio_data)},
    }


@router.post("/synthesize")
async def synthesize_speech(
    request: SynthesizeRequest,
    user_id: str = Depends(get_current_user),
):
    """Convert text to speech audio."""
    audio = await voice_service.synthesize_speech(
        text=request.text,
        voice=request.voice,
        speed=request.speed,
    )
    from fastapi.responses import Response
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=speech.wav"},
    )


@router.post("/command")
async def parse_command(
    text: str,
    user_id: str = Depends(get_current_user),
):
    """Parse a voice command without audio."""
    command = await voice_service.parse_voice_command(text)
    return {"success": True, "data": command}


@router.post("/process")
async def process_voice(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Full voice processing: transcribe → parse → route."""
    audio_data = await file.read()
    format = file.filename.split(".")[-1] if file.filename else "wav"

    result = await voice_service.process_voice_input(audio_data, format=format)
    return result


@router.get("/status")
async def voice_status(
    user_id: str = Depends(get_current_user),
):
    """Get voice service status."""
    return {"success": True, "data": voice_service.to_dict()}
