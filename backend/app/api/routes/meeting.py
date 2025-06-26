"""Meeting API routes for MeetingBaaS integration"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging
import uuid

from app.models.database import get_db
from app.services.meeting_service import meeting_service
from app.services import audio_handler
from app.schemas.meeting import (
    JoinMeetingRequest,
    JoinMeetingResponse,
    MeetingStatusResponse,
    WebhookEvent
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meeting", tags=["meeting"])


@router.options("/join")
async def join_meeting_options():
    return {"status": "ok"}

@router.post("/join", response_model=JoinMeetingResponse)
async def join_meeting(
    request: JoinMeetingRequest,
    db: AsyncSession = Depends(get_db)
) -> JoinMeetingResponse:
    """Join a Zoom meeting with the AI assistant bot"""
    try:
        # Validate meeting URL
        meeting_platforms = ['zoom', 'teams', 'meet', 'webex', 'gotomeeting', 'bluejeans']
        is_valid_url = any(platform in request.meeting_url.lower() for platform in meeting_platforms)
        
        if not is_valid_url:
            raise HTTPException(
                status_code=400,
                detail="Invalid meeting URL. Please provide a valid Zoom, Teams, or other supported meeting URL."
            )
        
        # Join meeting
        result = await meeting_service.join_meeting(
            meeting_url=request.meeting_url,
            bot_name=request.bot_name or "AI Executive Assistant",
            db=db
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return JoinMeetingResponse(
            bot_id=result["bot_id"],
            message=result["message"],
            status="joining"
        )
        
    except Exception as e:
        logger.error(f"Error joining meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leave/{bot_id}")
async def leave_meeting(bot_id: str) -> Dict[str, Any]:
    """Leave a meeting"""
    try:
        result = await meeting_service.leave_meeting(bot_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error leaving meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_meetings() -> List[Dict[str, Any]]:
    """Get list of active meeting bots"""
    try:
        return list(meeting_service.active_bots.values())
    except Exception as e:
        logger.error(f"Error getting active meetings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def meeting_webhook(
    event: WebhookEvent,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Handle webhook events from MeetingBaaS"""
    try:
        logger.info("Webhook Event")
        logger.info(f"Received webhook event: {event.event}")
        
        # Process webhook
        result = await meeting_service.process_webhook(event.dict(), db)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/transcripts/{bot_id}")
async def get_meeting_transcripts(
    bot_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get transcripts for a specific meeting"""
    try:
        from app.models.conversation import Meeting
        from sqlalchemy import select
        
        # Get meeting from database
        meeting = (await db.execute(
            select(Meeting).where(Meeting.bot_id == bot_id)
        )).scalar_one_or_none()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if not meeting.transcript:
            # Try to fetch from MeetingBaaS
            meeting_data = await meeting_service.fetch_meeting_data(bot_id)
            if meeting_data and meeting_data.get("bot_data"):
                transcripts = meeting_data["bot_data"].get("transcripts", [])
                return {
                    "bot_id": bot_id,
                    "transcripts": transcripts,
                    "status": meeting.status
                }
            else:
                return {
                    "bot_id": bot_id,
                    "transcripts": [],
                    "status": meeting.status,
                    "message": "No transcripts available yet"
                }
        
        return {
            "bot_id": bot_id,
            "transcripts": meeting.transcript,
            "status": meeting.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcripts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/speakers/{bot_id}")
async def get_meeting_speakers(bot_id: str) -> Dict[str, Any]:
    """Get speakers and current speaker for a meeting"""
    try:
        result = meeting_service.get_speakers(bot_id)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {
            "bot_id": bot_id,
            "speakers": result.get("speakers", []),
            "current_speaker": result.get("current_speaker"),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting speakers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
