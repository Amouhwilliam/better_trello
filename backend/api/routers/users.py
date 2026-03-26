from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import get_current_user_id, get_user_service
from api.schemas.user import PaginatedUsersResponse, UserCreate, UserResponse, UserUpdate
from application.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def get_me(
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
):
    return UserResponse.from_domain(service.get_user(current_user_id))


@router.get(
    "",
    response_model=PaginatedUsersResponse,
    summary="List users (paginated)",
    description="Returns a paginated list of users.",
)
def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(6, ge=1, le=100, description="Number of users per page"),
    service: UserService = Depends(get_user_service),
    _: UUID = Depends(get_current_user_id),
):
    all_users = service.get_all_users()
    total = len(all_users)
    skip = (page - 1) * page_size
    items = all_users[skip : skip + page_size]
    return PaginatedUsersResponse(
        items=[UserResponse.from_domain(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + page_size) < total,
    )


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
