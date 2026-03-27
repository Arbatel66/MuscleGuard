from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import session_user

from db.database import get_session
from models.User import User
from services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/create", response_model=User)
async def create_user(user_data: User, db: AsyncSession = Depends(get_session)):
    return await UserService.create_new_user(db, user_data)

@router.get("/{session_id}")
async def get_user_by_id(
    session_id: str,  # 路径参数
    db: AsyncSession = Depends(get_session)
):
    user = await UserService.get_user_by_id(db, session_id=session_id)
    if user is None:
        return "用户不存在"
    return user