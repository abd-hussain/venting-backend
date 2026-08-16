from fastapi import APIRouter

router = APIRouter()

# Endpoints live in this package, e.g.:
# POST /v1/auth/register  →  @router.post("/register")
# POST /v1/auth/login     →  @router.post("/login")
