from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_session
from schemas.SessionManager import ChatRequest
from fastapi import  Request

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/ai_chat")
async def ai_chat(
    request : Request,
    chat_in: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    fit_agent = request.app.state.fit_agent

    # # 默认清空一次记录
    # await fit_agent.clear_thread("chat_12A3C")

    reply = await fit_agent.lg_chat(
        db=db,
        session_id=chat_in.session_id,
        user_message=chat_in.message,
    )
    return {"reply": reply}


