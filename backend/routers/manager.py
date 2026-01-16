from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date

from database import get_db
from auth import get_manager_user, get_password_hash
from models import User, Keyword, KPI, Shift, UserShift, Request, Department
from schemas import (
    UserResponse, UserCreate, UserUpdate,
    KeywordResponse, KeywordCreate, KeywordUpdate,
    KPIResponse, KPICreate, KPIUpdate,
    ShiftResponse, ShiftCreate, ShiftUpdate,
    UserShiftResponse, UserShiftCreate, UserShiftUpdate,
    RequestResponse, RequestUpdate, RequestWithUser
)

router = APIRouter(prefix="/api/manager", tags=["Manager"])

# ============= Staff Management =============
@router.get("/staff", response_model=List[UserResponse])
async def get_department_staff(
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Lấy danh sách TẤT CẢ nhân viên trong hệ thống"""
    
    # Lấy tất cả staff, không phân biệt phòng ban
    staff = db.query(User).filter(
        User.role == "staff",
        User.is_active == True
    ).offset(skip).limit(limit).all()
    
    return staff

@router.post("/staff", response_model=UserResponse)
async def create_staff(
    user_data: UserCreate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Tạo nhân viên mới trong phòng ban"""
    
    if not current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manager chưa được gán phòng ban"
        )
    
    # Kiểm tra email
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng"
        )
    
    # Chỉ cho phép tạo staff trong phòng ban của mình
    if user_data.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager chỉ có thể tạo tài khoản staff"
        )
    
    if user_data.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ có thể tạo nhân viên trong phòng ban của mình"
        )
    
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role="staff",
        department_id=current_user.department_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.put("/staff/{staff_id}", response_model=UserResponse)
async def update_staff(
    staff_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin nhân viên"""
    
    staff = db.query(User).filter(
        User.id == staff_id,
        User.department_id == current_user.department_id,
        User.role == "staff"
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhân viên trong phòng ban"
        )
    
    if user_data.email:
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != staff_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được sử dụng"
            )
        staff.email = user_data.email
    
    if user_data.full_name:
        staff.full_name = user_data.full_name
    if user_data.phone is not None:
        staff.phone = user_data.phone
    if user_data.is_active is not None:
        staff.is_active = user_data.is_active
    
    db.commit()
    db.refresh(staff)
    
    return staff

@router.delete("/staff/{staff_id}")
async def delete_staff(
    staff_id: int,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Xóa nhân viên (soft delete)"""
    
    staff = db.query(User).filter(
        User.id == staff_id,
        User.department_id == current_user.department_id,
        User.role == "staff"
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhân viên trong phòng ban"
        )
    
    staff.is_active = False
    db.commit()
    
    return {"message": "Đã xóa nhân viên thành công"}

# ============= KPI Management =============
@router.get("/kpis", response_model=List[KPIResponse])
async def get_department_kpis(
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db),
    user_id: Optional[int] = None
):
    """Lấy danh sách KPI của phòng ban"""
    
    query = db.query(KPI).join(User).filter(
        User.department_id == current_user.department_id
    )
    
    if user_id:
        query = query.filter(KPI.user_id == user_id)
    
    kpis = query.all()
    return kpis

@router.post("/kpis", response_model=KPIResponse)
async def create_kpi(
    kpi_data: KPICreate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Tạo KPI mới cho nhân viên"""
    
    # Kiểm tra user có trong phòng ban không
    user = db.query(User).filter(
        User.id == kpi_data.user_id,
        User.department_id == current_user.department_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhân viên trong phòng ban"
        )
    
    new_kpi = KPI(**kpi_data.dict())
    db.add(new_kpi)
    db.commit()
    db.refresh(new_kpi)
    
    return new_kpi

@router.put("/kpis/{kpi_id}", response_model=KPIResponse)
async def update_kpi(
    kpi_id: int,
    kpi_data: KPIUpdate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Cập nhật KPI"""
    
    kpi = db.query(KPI).join(User).filter(
        KPI.id == kpi_id,
        User.department_id == current_user.department_id
    ).first()
    
    if not kpi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy KPI"
        )
    
    for key, value in kpi_data.dict(exclude_unset=True).items():
        setattr(kpi, key, value)
    
    db.commit()
    db.refresh(kpi)
    
    return kpi

@router.delete("/kpis/{kpi_id}")
async def delete_kpi(
    kpi_id: int,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Xóa KPI"""
    
    kpi = db.query(KPI).join(User).filter(
        KPI.id == kpi_id,
        User.department_id == current_user.department_id
    ).first()
    
    if not kpi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy KPI"
        )
    
    db.delete(kpi)
    db.commit()
    
    return {"message": "Đã xóa KPI thành công"}

# ============= Keyword Management =============
@router.get("/keywords", response_model=List[KeywordResponse])
async def get_department_keywords(
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách TẤT CẢ từ khóa trong hệ thống"""
    
    # Lấy tất cả keywords, không phân biệt phòng ban
    keywords = db.query(Keyword).all()
    
    return keywords

@router.post("/keywords", response_model=KeywordResponse)
async def create_keyword(
    keyword_data: KeywordCreate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Tạo từ khóa mới"""
    
    # Chỉ cho phép tạo keyword cho phòng ban của mình
    if keyword_data.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ có thể tạo từ khóa cho phòng ban của mình"
        )
    
    new_keyword = Keyword(**keyword_data.dict())
    db.add(new_keyword)
    db.commit()
    db.refresh(new_keyword)
    
    return new_keyword

@router.put("/keywords/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    keyword_data: KeywordUpdate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Cập nhật từ khóa"""
    
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.department_id == current_user.department_id
    ).first()
    
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy từ khóa"
        )
    
    for key, value in keyword_data.dict(exclude_unset=True).items():
        setattr(keyword, key, value)
    
    db.commit()
    db.refresh(keyword)
    
    return keyword

@router.delete("/keywords/{keyword_id}")
async def delete_keyword(
    keyword_id: int,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Xóa từ khóa"""
    
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.department_id == current_user.department_id
    ).first()
    
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy từ khóa"
        )
    
    db.delete(keyword)
    db.commit()
    
    return {"message": "Đã xóa từ khóa thành công"}

# ============= Shift Management =============
@router.get("/shifts", response_model=List[ShiftResponse])
async def get_department_shifts(
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách ca làm việc của phòng ban"""
    
    shifts = db.query(Shift).filter(
        Shift.department_id == current_user.department_id
    ).all()
    
    return shifts

@router.post("/shifts", response_model=ShiftResponse)
async def create_shift(
    shift_data: ShiftCreate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Tạo ca làm việc mới"""
    
    if shift_data.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ có thể tạo ca làm việc cho phòng ban của mình"
        )
    
    new_shift = Shift(**shift_data.dict())
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    
    return new_shift

@router.put("/shifts/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: int,
    shift_data: ShiftUpdate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Cập nhật ca làm việc"""
    
    shift = db.query(Shift).filter(
        Shift.id == shift_id,
        Shift.department_id == current_user.department_id
    ).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ca làm việc"
        )
    
    for key, value in shift_data.dict(exclude_unset=True).items():
        setattr(shift, key, value)
    
    db.commit()
    db.refresh(shift)
    
    return shift

@router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: int,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Xóa ca làm việc"""
    
    shift = db.query(Shift).filter(
        Shift.id == shift_id,
        Shift.department_id == current_user.department_id
    ).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ca làm việc"
        )
    
    db.delete(shift)
    db.commit()
    
    return {"message": "Đã xóa ca làm việc thành công"}

# ============= Shift Assignment =============
@router.post("/shift-assignments", response_model=UserShiftResponse)
async def assign_shift_to_staff(
    assignment_data: UserShiftCreate,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Phân công ca làm việc cho nhân viên"""
    
    # Kiểm tra staff có trong phòng ban không
    staff = db.query(User).filter(
        User.id == assignment_data.user_id,
        User.department_id == current_user.department_id,
        User.role == "staff"
    ).first()
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhân viên trong phòng ban"
        )
    
    # Kiểm tra shift có thuộc phòng ban không
    shift = db.query(Shift).filter(
        Shift.id == assignment_data.shift_id,
        Shift.department_id == current_user.department_id
    ).first()
    
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy ca làm việc trong phòng ban"
        )
    
    # Kiểm tra đã có assignment chưa
    existing = db.query(UserShift).filter(
        UserShift.user_id == assignment_data.user_id,
        UserShift.shift_id == assignment_data.shift_id,
        UserShift.date == assignment_data.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nhân viên đã được phân công ca này trong ngày"
        )
    
    new_assignment = UserShift(**assignment_data.dict())
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    
    return new_assignment

@router.get("/shift-assignments", response_model=List[UserShiftResponse])
async def get_shift_assignments(
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db),
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Lấy danh sách phân công ca làm việc"""
    
    query = db.query(UserShift).join(User).filter(
        User.department_id == current_user.department_id
    )
    
    if user_id:
        query = query.filter(UserShift.user_id == user_id)
    if start_date:
        query = query.filter(UserShift.date >= start_date)
    if end_date:
        query = query.filter(UserShift.date <= end_date)
    
    assignments = query.all()
    return assignments

# ============= Request Approval =============
@router.get("/requests", response_model=List[RequestWithUser])
async def get_department_requests(
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None
):
    """Lấy danh sách TẤT CẢ yêu cầu từ nhân viên trong hệ thống"""
    
    # Lấy tất cả requests từ staff, không phân biệt phòng ban
    query = db.query(Request).join(User).filter(
        User.role == "staff"
    )
    
    if status_filter:
        query = query.filter(Request.status == status_filter)
    
    requests = query.all()
    
    result = []
    for req in requests:
        reviewer_name = None
        if req.reviewed_by:
            reviewer = db.query(User).filter(User.id == req.reviewed_by).first()
            if reviewer:
                reviewer_name = reviewer.full_name
        
        result.append({
            "id": req.id,
            "user_id": req.user_id,
            "type": req.type,
            "title": req.title,
            "description": req.description,
            "status": req.status,
            "reviewed_by": req.reviewed_by,
            "reviewed_at": req.reviewed_at,
            "review_notes": req.review_notes,
            "created_at": req.created_at,
            "user_name": req.user.full_name,
            "reviewer_name": reviewer_name
        })
    
    return result

@router.put("/requests/{request_id}/approve")
async def approve_request(
    request_id: int,
    review_notes: Optional[str] = None,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Phê duyệt yêu cầu"""
    
    request = db.query(Request).join(User).filter(
        Request.id == request_id,
        User.department_id == current_user.department_id
    ).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy yêu cầu"
        )
    
    if request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yêu cầu đã được xử lý"
        )
    
    request.status = "approved"
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.utcnow()
    request.review_notes = review_notes
    
    db.commit()
    
    return {"message": "Đã phê duyệt yêu cầu"}

@router.put("/requests/{request_id}/reject")
async def reject_request(
    request_id: int,
    review_notes: Optional[str] = None,
    current_user: User = Depends(get_manager_user),
    db: Session = Depends(get_db)
):
    """Từ chối yêu cầu"""
    
    request = db.query(Request).join(User).filter(
        Request.id == request_id,
        User.department_id == current_user.department_id
    ).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy yêu cầu"
        )
    
    if request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yêu cầu đã được xử lý"
        )
    
    request.status = "rejected"
    request.reviewed_by = current_user.id
    request.reviewed_at = datetime.utcnow()
    request.review_notes = review_notes
    
    db.commit()
    
    return {"message": "Đã từ chối yêu cầu"}
