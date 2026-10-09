"""Read-only global assistant skills catalog."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_agent_surface_json
from app.panel.deps import get_db
from app.services.prompts import load_assistant_config
from app.services.skills import global_skill_index

router = APIRouter(tags=["panel-api-skills"])


@router.get("/skills")
def list_skills(
    session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)
) -> dict:
    del session, current
    skills = global_skill_index(load_assistant_config())
    return {
        "skills": [
            {"name": skill.name, "description": skill.description, "scope": "global"}
            for skill in skills
        ]
    }
