"""Read-only global assistant skills catalog."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_agent_surface_json
from app.panel.deps import get_db
from app.services.prompts import load_assistant_config
from app.services.skills import SkillDefinition, SkillError, global_skill_index, load_skill_body

router = APIRouter(tags=["panel-api-skills"])


@router.get("/skills")
def list_skills(
    session: Session = Depends(get_db), current: User = Depends(require_agent_surface_json)
) -> dict:
    del session, current
    skills = global_skill_index(load_assistant_config())
    return {"skills": [_skill_payload(skill) for skill in skills]}


def _skill_payload(skill: SkillDefinition) -> dict:
    """Expose the declared body so the panel can preview a skill read-only.

    A missing or unreadable body degrades to ``None`` instead of failing the whole
    catalog: the name and description are still useful on their own.
    """
    try:
        body = load_skill_body(skill)
    except SkillError:
        body = None
    return {"name": skill.name, "description": skill.description, "scope": "global", "body": body}
