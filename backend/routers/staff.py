from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from database import get_db
from auth import get_staff_user, get_current_user
from models import User, Message, MessageAssignment, Customer, Request, Notification
from schemas import (
    MessageWithCustomer, MessageUpdate,
    CustomerResponse,
    RequestResponse, RequestCreate,
    NotificationResponse
)

router = APIRouter(prefix="/api/staff", tags=["Staff"])

# ============= Messages =============
@router.get("/messages", response_model=List[MessageWithCustomer])
async def get_assigned_messages(
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """Lấy danh sách tin nhắn được giao"""
    
    query = db.query(Message).join(MessageAssignment).filter(
        MessageAssignment.assigned_to == current_user.id
    )
    
    if status_filter:
        query = query.filter(Message.status == status_filter)
    
    messages = query.order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for msg in messages:
        customer = db.query(Customer).filter(Customer.id == msg.customer_id).first()
        result.append({
            "id": msg.id,
            "customer_id": msg.customer_id,
            "content": msg.content,
            "platform": msg.platform,
            "direction": msg.direction,
            "status": msg.status,
            "external_id": msg.external_id,
            "created_at": msg.created_at,
            "customer_name": customer.name if customer else None,
            "customer_phone": customer.phone if customer else None
        })
    
    return result

@router.get("/messages/{message_id}", response_model=MessageWithCustomer)
async def get_message_detail(
    message_id: int,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Lấy chi tiết tin nhắn"""
    
    message = db.query(Message).join(MessageAssignment).filter(
        Message.id == message_id,
        MessageAssignment.assigned_to == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn hoặc bạn không có quyền truy cập"
        )
    
    customer = db.query(Customer).filter(Customer.id == message.customer_id).first()
    
    return {
        "id": message.id,
        "customer_id": message.customer_id,
        "content": message.content,
        "platform": message.platform,
        "direction": message.direction,
        "status": message.status,
        "external_id": message.external_id,
        "created_at": message.created_at,
        "customer_name": customer.name if customer else None,
        "customer_phone": customer.phone if customer else None
    }

@router.put("/messages/{message_id}/complete")
async def mark_message_complete(
    message_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu tin nhắn đã hoàn thành"""
    
    # Kiểm tra message có được giao cho user không
    assignment = db.query(MessageAssignment).filter(
        MessageAssignment.message_id == message_id,
        MessageAssignment.assigned_to == current_user.id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn hoặc bạn không có quyền truy cập"
        )
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if message.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tin nhắn đã được đánh dấu hoàn thành"
        )
    
    # Cập nhật trạng thái
    message.status = "completed"
    assignment.completed_at = datetime.utcnow()
    if notes:
        assignment.notes = notes
    
    db.commit()
    
    return {"message": "Đã đánh dấu tin nhắn hoàn thành"}

@router.put("/messages/{message_id}/in-progress")
async def mark_message_in_progress(
    message_id: int,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu tin nhắn đang xử lý"""
    
    assignment = db.query(MessageAssignment).filter(
        MessageAssignment.message_id == message_id,
        MessageAssignment.assigned_to == current_user.id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn hoặc bạn không có quyền truy cập"
        )
    
    message = db.query(Message).filter(Message.id == message_id).first()
    message.status = "in_progress"
    
    db.commit()
    
    return {"message": "Đã đánh dấu tin nhắn đang xử lý"}

# ============= Customers =============
@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer_info(
    customer_id: int,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Xem thông tin khách hàng"""
    
    # Kiểm tra staff có được giao tin nhắn của customer này không
    has_access = db.query(MessageAssignment).join(Message).filter(
        Message.customer_id == customer_id,
        MessageAssignment.assigned_to == current_user.id
    ).first()
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem thông tin khách hàng này"
        )
    
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy khách hàng"
        )
    
    return customer

# ============= Requests =============
@router.get("/requests", response_model=List[RequestResponse])
async def get_my_requests(
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None
):
    """Lấy danh sách yêu cầu của mình"""
    
    query = db.query(Request).filter(Request.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(Request.status == status_filter)
    
    requests = query.order_by(Request.created_at.desc()).all()
    
    return requests

@router.post("/requests", response_model=RequestResponse)
async def create_request(
    request_data: RequestCreate,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Tạo yêu cầu nội bộ mới (nghỉ phép, tăng lương, v.v.)"""
    
    new_request = Request(
        user_id=current_user.id,
        type=request_data.type,
        title=request_data.title,
        description=request_data.description
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    # Tạo thông báo cho manager
    if current_user.department_id:
        managers = db.query(User).filter(
            User.department_id == current_user.department_id,
            User.role == "manager",
            User.is_active == True
        ).all()
        
        for manager in managers:
            notification = Notification(
                user_id=manager.id,
                title="Yêu cầu mới từ nhân viên",
                message=f"{current_user.full_name} đã tạo yêu cầu: {request_data.title}",
                type="request",
                link=f"/manager/requests/{new_request.id}"
            )
            db.add(notification)
        
        db.commit()
    
    return new_request

@router.get("/requests/{request_id}", response_model=RequestResponse)
async def get_request_detail(
    request_id: int,
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Xem chi tiết yêu cầu"""
    
    request = db.query(Request).filter(
        Request.id == request_id,
        Request.user_id == current_user.id
    ).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy yêu cầu"
        )
    
    return request

# ============= Profile =============
@router.get("/profile", response_model=dict)
async def get_my_profile(
    current_user: User = Depends(get_staff_user),
    db: Session = Depends(get_db)
):
    """Xem thông tin cá nhân và hiệu suất"""
    
    # Thông tin cơ bản
    profile = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role,
        "department_name": current_user.department.name if current_user.department else None
    }
    
    # Thống kê hiệu suất
    total_messages = db.query(MessageAssignment).filter(
        MessageAssignment.assigned_to == current_user.id
    ).count()
    
    completed_messages = db.query(MessageAssignment).join(Message).filter(
        MessageAssignment.assigned_to == current_user.id,
        Message.status == "completed"
    ).count()
    
    pending_messages = db.query(MessageAssignment).join(Message).filter(
        MessageAssignment.assigned_to == current_user.id,
        Message.status.in_(["pending", "assigned", "in_progress"])
    ).count()
    
    profile["performance"] = {
        "total_messages": total_messages,
        "completed_messages": completed_messages,
        "pending_messages": pending_messages,
        "completion_rate": round((completed_messages / total_messages * 100) if total_messages > 0 else 0, 2)
    }
    
    return profile

# ============= Notifications =============
@router.get("/notifications", response_model=List[NotificationResponse])
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20
):
    """Lấy danh sách thông báo"""
    
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return notifications

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Đánh dấu thông báo đã đọc"""
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Đã đánh dấu thông báo đã đọc"}
