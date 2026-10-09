from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_admin_json
from app.panel.api.serializers import to_installation_dict, to_recipe_dict
from app.panel.deps import get_db
from app.services import automation_installations
from app.services.recipes import RECIPES

router = APIRouter(tags=["panel-api-automation-recipes"])


class InstallationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_id: str
    parameters: dict[str, object]


class ParametersBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parameters: dict[str, object]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="automation installation not found")


def _installation(session: Session, installation_id: int):
    installation = automation_installations.get_installation(session, installation_id)
    if installation is None:
        raise _not_found()
    return installation


@router.get("/automation-recipes")
def list_recipes(current: User = Depends(require_admin_json)) -> dict:
    return {"recipes": [to_recipe_dict(recipe) for recipe in RECIPES.values()]}


@router.get("/automation-installations")
def list_installations(session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    try:
        return {"installations": [to_installation_dict(item) for item in automation_installations.list_installations(session)]}
    except Exception:
        session.rollback()
        raise


@router.post("/automation-installations", status_code=status.HTTP_201_CREATED)
def create_installation(body: InstallationBody, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    try:
        installation = automation_installations.install(session, body.recipe_id, body.parameters, actor=current.username)
        session.commit()
        return {"installation": to_installation_dict(installation)}
    except automation_installations.RecipeAlreadyInstalled:
        session.rollback()
        raise HTTPException(status_code=409, detail="recipe already installed")
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="recipe already installed")
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    except Exception:
        session.rollback()
        raise


@router.patch("/automation-installations/{installation_id}")
def update_installation(installation_id: int, body: ParametersBody, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    try:
        installation = _installation(session, installation_id)
        automation_installations.update_parameters(session, installation, body.parameters, actor=current.username)
        session.commit()
        return {"installation": to_installation_dict(installation)}
    except HTTPException:
        session.rollback()
        raise
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    except Exception:
        session.rollback()
        raise


def _set_enabled(installation_id: int, enabled: bool, session: Session, current: User) -> dict:
    try:
        installation = _installation(session, installation_id)
        automation_installations.set_enabled(session, installation, enabled, actor=current.username)
        session.commit()
        return {"ok": True, "installation": to_installation_dict(installation)}
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise


@router.post("/automation-installations/{installation_id}/enable")
def enable_installation(installation_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return _set_enabled(installation_id, True, session, current)


@router.post("/automation-installations/{installation_id}/disable")
def disable_installation(installation_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return _set_enabled(installation_id, False, session, current)
