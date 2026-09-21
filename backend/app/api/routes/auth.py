from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register():
    """
    User registration endpoint.
    TODO: Implementation in Authentication module (Prompt 2).
    """
    return {"message": "Registration endpoint ready for authentication pipeline."}


@router.post("/login")
async def login():
    """
    User login endpoint issuing JWT.
    TODO: Implementation in Authentication module (Prompt 2).
    """
    return {"message": "Login endpoint ready for authentication pipeline."}
