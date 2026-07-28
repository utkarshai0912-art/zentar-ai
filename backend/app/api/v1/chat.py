"""
Zentar Intelligence — Chat API Routes

Conversation management and streaming AI chat.
"""

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.conversation import Conversation, Message
from app.schemas import (
    APIResponse,
    ChatRequest,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageResponse,
    PaginatedResponse,
)
from app.services.ai_service import provider_registry

router = APIRouter(prefix="/chat", tags=["Chat"])


# ──────────────────────────────────────────
# Conversation CRUD
# ──────────────────────────────────────────

@router.get("/conversations", response_model=APIResponse[PaginatedResponse[ConversationResponse]])
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    archived: bool = False,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user."""
    from sqlalchemy import select, func

    # Total count
    count_q = select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.is_archived == archived,
        Conversation.is_deleted == False,
    )
    total = (await db.execute(count_q)).scalar()

    # Paginated query
    q = (
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == archived,
            Conversation.is_deleted == False,
        )
        .order_by(Conversation.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    conversations = result.scalars().all()

    items = [
        ConversationResponse(
            id=c.id,
            title=c.title,
            model_id=c.model_id,
            provider=c.provider,
            temperature=c.temperature,
            max_tokens=c.max_tokens,
            is_archived=c.is_archived,
            is_pinned=c.is_pinned,
            message_count=c.message_count,
            created_at=c.created_at,
            updated_at=c.updated_at,
            messages=[],
        )
        for c in conversations
    ]

    return APIResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@router.post("/conversations", response_model=APIResponse[ConversationResponse])
async def create_conversation(
    request: ConversationCreateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    conversation = Conversation(
        user_id=user_id,
        title=request.title or "New Conversation",
        model_id=request.model_id,
        provider=request.provider,
        system_prompt=request.system_prompt,
        temperature=request.temperature or 0.7,
        max_tokens=request.max_tokens or 4096,
    )
    db.add(conversation)
    await db.flush()

    return APIResponse(
        message="Conversation created",
        data=ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            model_id=conversation.model_id,
            provider=conversation.provider,
            temperature=conversation.temperature,
            max_tokens=conversation.max_tokens,
            is_archived=conversation.is_archived,
            is_pinned=conversation.is_pinned,
            message_count=0,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        ),
    )


@router.get("/conversations/{conv_id}", response_model=APIResponse[ConversationResponse])
async def get_conversation(
    conv_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all its messages."""
    from sqlalchemy import select

    q = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == user_id,
        Conversation.is_deleted == False,
    )
    result = await db.execute(q)
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            content_type=m.content_type,
            input_tokens=m.input_tokens,
            output_tokens=m.output_tokens,
            total_tokens=m.total_tokens,
            status=m.status,
            provider=m.provider,
            model=m.model,
            created_at=m.created_at,
        )
        for m in conversation.messages
    ]

    return APIResponse(
        data=ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            model_id=conversation.model_id,
            provider=conversation.provider,
            temperature=conversation.temperature,
            max_tokens=conversation.max_tokens,
            is_archived=conversation.is_archived,
            is_pinned=conversation.is_pinned,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages,
        ),
    )


@router.put("/conversations/{conv_id}", response_model=APIResponse[ConversationResponse])
async def update_conversation(
    conv_id: str,
    request: ConversationUpdateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update conversation properties."""
    from sqlalchemy import select

    q = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == user_id,
    )
    result = await db.execute(q)
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if request.title is not None:
        conversation.title = request.title
    if request.is_archived is not None:
        conversation.is_archived = request.is_archived
    if request.is_pinned is not None:
        conversation.is_pinned = request.is_pinned

    await db.flush()
    return APIResponse(
        message="Conversation updated",
        data=ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            model_id=conversation.model_id,
            provider=conversation.provider,
            temperature=conversation.temperature,
            max_tokens=conversation.max_tokens,
            is_archived=conversation.is_archived,
            is_pinned=conversation.is_pinned,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        ),
    )


@router.delete("/conversations/{conv_id}", response_model=APIResponse)
async def delete_conversation(
    conv_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a conversation."""
    from sqlalchemy import select

    q = select(Conversation).where(
        Conversation.id == conv_id,
        Conversation.user_id == user_id,
    )
    result = await db.execute(q)
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.is_deleted = True
    await db.flush()
    return APIResponse(message="Conversation deleted")


# ──────────────────────────────────────────
# Chat Completion
# ──────────────────────────────────────────

@router.post("/completions")
async def chat_completion(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response (supports streaming)."""
    # Get or create conversation
    conv_id = request.conversation_id
    if conv_id:
        from sqlalchemy import select
        q = select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.user_id == user_id,
        )
        result = await db.execute(q)
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            user_id=user_id,
            title=request.message[:80] + ("..." if len(request.message) > 80 else ""),
            model_id=request.model_id,
            provider=request.provider,
            system_prompt=request.system_prompt,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 4096,
        )
        db.add(conversation)
        await db.flush()
        conv_id = conversation.id

    # Save user message
    user_message = Message(
        conversation_id=conv_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    conversation.message_count += 1
    await db.flush()

    # Build message history for context
    from sqlalchemy import select
    msg_q = select(Message).where(
        Message.conversation_id == conv_id,
        Message.is_deleted == False,
    ).order_by(Message.created_at)
    msg_result = await db.execute(msg_q)
    history = msg_result.scalars().all()

    messages = []
    if request.system_prompt or conversation.system_prompt:
        messages.append({
            "role": "system",
            "content": request.system_prompt or conversation.system_prompt or "",
        })
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Streaming response
    async def generate():
        assistant_content = ""
        input_tokens = 0
        output_tokens = 0

        try:
            async for event in provider_registry.route_request(
                messages=messages,
                provider_name=request.provider or conversation.provider,
                model=request.model_id or conversation.model_id,
                temperature=request.temperature or conversation.temperature or 0.7,
                max_tokens=request.max_tokens or conversation.max_tokens or 4096,
                stream=request.stream,
            ):
                if event["type"] == "chunk":
                    assistant_content += event["content"]
                    yield f"data: {json.dumps(event)}\n\n"
                elif event["type"] == "done":
                    usage = event.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)

                    # Save assistant message
                    assistant_msg = Message(
                        conversation_id=conv_id,
                        role="assistant",
                        content=assistant_content,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        provider=event.get("provider"),
                        model=event.get("model"),
                    )
                    db.add(assistant_msg)
                    conversation.message_count += 1
                    await db.flush()

                    event["conversation_id"] = conv_id
                    yield f"data: {json.dumps(event)}\n\n"
                elif event["type"] == "error":
                    yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────
# WebSocket Chat
# ──────────────────────────────────────────

@router.websocket("/ws/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time chat with streaming."""
    from app.core.security import decode_token

    # Authenticate via token
    try:
        payload = decode_token(token)
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    db: AsyncSession = await anext(get_db())

    try:
        # Verify conversation
        from sqlalchemy import select
        q = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        result = await db.execute(q)
        conversation = result.scalar_one_or_none()
        if not conversation:
            await websocket.send_json({"type": "error", "error": "Conversation not found"})
            await websocket.close()
            return

        while True:
            data = await websocket.receive_json()
            message_content = data.get("message", "")

            if not message_content:
                continue

            # Save user message
            user_msg = Message(
                conversation_id=conversation_id,
                role="user",
                content=message_content,
            )
            db.add(user_msg)
            conversation.message_count += 1
            await db.flush()

            # Get history
            msg_q = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False,
            ).order_by(Message.created_at)
            msg_result = await db.execute(msg_q)
            history = msg_result.scalars().all()

            messages = []
            if conversation.system_prompt:
                messages.append({"role": "system", "content": conversation.system_prompt})
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

            # Stream response
            assistant_content = ""
            async for event in provider_registry.route_request(
                messages=messages,
                provider_name=conversation.provider,
                model=conversation.model_id,
                temperature=conversation.temperature,
                max_tokens=conversation.max_tokens,
                stream=True,
            ):
                await websocket.send_json(event)
                if event["type"] == "chunk":
                    assistant_content += event.get("content", "")

            # Save assistant message
            if assistant_content:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content,
                )
                db.add(assistant_msg)
                conversation.message_count += 1
                await db.flush()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
    finally:
        await db.close()
