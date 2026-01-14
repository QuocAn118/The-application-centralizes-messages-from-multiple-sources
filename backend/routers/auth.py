from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db
from auth import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from schemas import LoginRequest, Token, UserResponse
from models import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập và nhận JWT token
    
    - **email**: Email đăng nhập
    - **password**: Mật khẩu
    
    Tài khoản mẫu:
    - Admin: admin@omnichat.com / admin123
    - Manager: manager.sales@omnichat.com / manager123
    - Staff: staff1@omnichat.com / staff123
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Lấy thông tin người dùng hiện tại
    
    Yêu cầu: Bearer token trong header Authorization
    """
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Đăng xuất (client cần xóa token)
    
    Yêu cầu: Bearer token trong header Authorization
    """
    return {"message": "Đăng xuất thành công"}
