from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.session import get_db
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationRead
from app.services.ai_recommendation_service import generate_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"], dependencies=[Depends(require_role("admin"))])


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(db: Session = Depends(get_db)) -> list[Recommendation]:
    """Free to call as often as you like -- just reads whatever the last
    `POST /recommendations/generate` produced, no LLM call happens here."""
    return list(db.scalars(select(Recommendation).order_by(Recommendation.category)).all())


@router.post("/generate", response_model=list[RecommendationRead])
def generate(db: Session = Depends(get_db)) -> list[Recommendation]:
    """Runs the deterministic analysis and, if anything was found, exactly
    ONE Groq call to explain all of it -- replaces the previous set."""
    return generate_recommendations(db)
