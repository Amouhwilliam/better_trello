from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from api.dependencies import get_current_user_id, get_user_service
from api.schemas.user import UserCreate, UserResponse, UserUpdate
from application.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List all users",
)
def list_users(service: UserService = Depends(get_user_service), _: UUID = Depends(get_current_user_id)):
    return [UserResponse.from_domain(u) for u in service.get_all_users()]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by ID",
)
def get_user(user_id: UUID, service: UserService = Depends(get_user_service), _: UUID = Depends(get_current_user_id)):
    return UserResponse.from_domain(service.get_user(user_id))


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
def create_user(body: UserCreate, service: UserService = Depends(get_user_service)):
    user = service.create_user(fullname=body.fullname, email=body.email, password=body.password)
    return UserResponse.from_domain(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    description="Update fullname, email, and/or password.",
)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    service: UserService = Depends(get_user_service),
    _: UUID = Depends(get_current_user_id),
):
    user = service.update_user(
        user_id=user_id,
        fullname=body.fullname,
        email=body.email,
        password=body.password,
    )
    return UserResponse.from_domain(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
def delete_user(user_id: UUID, service: UserService = Depends(get_user_service), _: UUID = Depends(get_current_user_id)):
    service.delete_user(user_id)
