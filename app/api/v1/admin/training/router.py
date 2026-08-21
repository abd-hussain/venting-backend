from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.admin.deps import (
    AdminPrincipal,
    require_any_permission,
    require_permission,
)
from app.api.v1.admin.training.schemas import (
    AchievementResponse,
    AchievementUpsertRequest,
    InviteStatsResponse,
    ListenerTrainingResponse,
    TrainingModuleResponse,
    TrainingModuleUpsertRequest,
    VentorAchievementResponse,
)
from app.api.v1.admin.training.service import (
    force_complete_training,
    get_invite_stats,
    get_listener_training,
    grant_achievement,
    list_achievements,
    list_training_modules,
    upsert_achievements,
    upsert_training_modules,
)
from app.core.responses import success_response
from app.schemas.envelope import APIErrorResponse, APISuccessResponse

router = APIRouter(tags=["admin-training"])

TrainingReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("catalogs:write", "users:read")),
]
CatalogWriter = Annotated[
    AdminPrincipal, Depends(require_permission("catalogs:write"))
]
UserReader = Annotated[AdminPrincipal, Depends(require_permission("users:read"))]
UserWriter = Annotated[AdminPrincipal, Depends(require_permission("users:write"))]
InviteStatsReader = Annotated[
    AdminPrincipal,
    Depends(require_any_permission("analytics:read", "users:read")),
]


@router.get(
    "/training-modules",
    response_model=APISuccessResponse[list[TrainingModuleResponse]],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def training_modules_list(db: DbSession, _admin: TrainingReader):
    return success_response(
        [
            item.model_dump(mode="json")
            for item in list_training_modules(db)
        ]
    )


@router.put(
    "/training-modules",
    response_model=APISuccessResponse[list[TrainingModuleResponse]],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
)
def training_modules_upsert(
    body: TrainingModuleUpsertRequest | list[TrainingModuleUpsertRequest],
    db: DbSession,
    admin: CatalogWriter,
):
    return success_response(
        [
            item.model_dump(mode="json")
            for item in upsert_training_modules(db, body, admin)
        ]
    )


@router.get(
    "/listeners/{listener_id}/training",
    response_model=APISuccessResponse[ListenerTrainingResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def listener_training(
    listener_id: UUID,
    db: DbSession,
    _admin: UserReader,
):
    return success_response(
        get_listener_training(db, listener_id).model_dump(mode="json")
    )


@router.post(
    "/listeners/{listener_id}/training/{module_id}/complete",
    response_model=APISuccessResponse[ListenerTrainingResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def listener_training_complete(
    listener_id: UUID,
    module_id: str,
    db: DbSession,
    admin: UserWriter,
):
    return success_response(
        force_complete_training(db, listener_id, module_id, admin).model_dump(
            mode="json"
        )
    )


@router.get(
    "/achievements",
    response_model=APISuccessResponse[list[AchievementResponse]],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def achievements_list(db: DbSession, _admin: UserReader):
    return success_response(
        [item.model_dump(mode="json") for item in list_achievements(db)]
    )


@router.put(
    "/achievements",
    response_model=APISuccessResponse[list[AchievementResponse]],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        422: {"model": APIErrorResponse},
    },
)
def achievements_upsert(
    body: AchievementUpsertRequest | list[AchievementUpsertRequest],
    db: DbSession,
    admin: CatalogWriter,
):
    return success_response(
        [
            item.model_dump(mode="json")
            for item in upsert_achievements(db, body, admin)
        ]
    )


@router.post(
    "/ventors/{ventor_id}/achievements/{achievement_id}",
    response_model=APISuccessResponse[VentorAchievementResponse],
    responses={
        401: {"model": APIErrorResponse},
        403: {"model": APIErrorResponse},
        404: {"model": APIErrorResponse},
    },
)
def ventor_achievement_grant(
    ventor_id: UUID,
    achievement_id: str,
    db: DbSession,
    admin: UserWriter,
):
    return success_response(
        grant_achievement(db, ventor_id, achievement_id, admin).model_dump(
            mode="json"
        )
    )


@router.get(
    "/invite-stats",
    response_model=APISuccessResponse[InviteStatsResponse],
    responses={401: {"model": APIErrorResponse}, 403: {"model": APIErrorResponse}},
)
def invite_stats(db: DbSession, _admin: InviteStatsReader):
    return success_response(get_invite_stats(db).model_dump(mode="json"))
