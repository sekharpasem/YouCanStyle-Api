# Register API should check with the mobile number instead of Email for user existance
@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate) -> Any:
    """Register a new user."""
    # Check if user already exists
    existing_user = await get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists."
        )
    
    # Create new user
    user = await create_user(user_in)
    return user
