"""Authentication API routes."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.services.auth import AuthError, UserAlreadyExistsError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token",
        )
    return token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request) -> AuthResponse:
    auth_service = request.app.state.auth_service
    try:
        user = auth_service.register_user(req.name, req.email, req.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from exc

    token = auth_service.issue_token(user)
    return AuthResponse(token=token, user=UserPublic.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, request: Request) -> AuthResponse:
    auth_service = request.app.state.auth_service
    try:
        user = auth_service.authenticate(req.email, req.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    token = auth_service.issue_token(user)
    return AuthResponse(token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=AuthResponse)
async def me(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthResponse:
    auth_service = request.app.state.auth_service
    token = _extract_bearer_token(authorization)
    try:
        user = auth_service.get_user_from_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return AuthResponse(token=token, user=UserPublic.model_validate(user))
