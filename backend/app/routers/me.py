from fastapi import APIRouter, Depends

from app.access import compute_access, days_to_exam
from app.config import settings
from app.dependencies import get_current_user
from app.schemas import AccessInfo, MeResponse

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user)):
    """Текущий пользователь: профиль, доступ и дней до экзамена."""
    return MeResponse(
        id=user["telegram_id"],
        first_name=user.get("first_name"),
        username=user.get("username"),
        access=AccessInfo(**compute_access(user.get("access_until"))),
        days_to_exam=days_to_exam(settings.exam_date),
        exam_date=settings.exam_date or None,
    )