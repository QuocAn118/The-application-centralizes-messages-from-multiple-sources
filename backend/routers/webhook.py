from fastapi import APIRouter, Depends, HTTPException, status, Request as FastAPIRequest
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from database import get_db
from models import Customer, Message, Notification, User
from keyword_analyzer import KeywordAnalyzer
from schemas import ZaloWebhookMessage

router = APIRouter(prefix="/api/webhook", tags=["Webhooks"])

logger = logging.getLogger(__name__)

@router.post("/zalo")
async def zalo_webhook(
    request: FastAPIRequest,
    db: Session = Depends(get_db)
):
    """
    Webhook nhận tin nhắn từ Zalo OA
    
    Đây là mock endpoint để demo. Trong production cần:
    - Verify webhook signature
    - Handle các event types khác nhau
    - Rate limiting
    """
    
    try:
        data = await request.json()
        logger.info(f"Received Zalo webhook: {data}")
        
        # Mock processing - trong thực tế cần parse theo Zalo API format
        event_name = data.get("event_name", "")
        
        if event_name == "user_send_text":
            # Xử lý tin nhắn text từ user
            user_id = data.get("sender", {}).get("id")
            message_text = data.get("message", {}).get("text", "")
            message_id = data.get("message_id")
            
            # Tìm hoặc tạo customer
            customer = db.query(Customer).filter(Customer.zalo_id == user_id).first()
            if not customer:
                customer = Customer(
                    zalo_id=user_id,
                    platform="zalo",
                    name=f"Khách hàng Zalo {user_id}"
                )
                db.add(customer)
                db.commit()
                db.refresh(customer)
            
            # Tạo message
            new_message = Message(
                customer_id=customer.id,
                content=message_text,
                platform="zalo",
                external_id=message_id,
                direction="incoming",
                status="pending"
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            
            # Tự động giao việc
            analyzer = KeywordAnalyzer(db)
            assignment = analyzer.auto_assign_message(new_message)
            
            if assignment:
                # Tạo thông báo cho staff được giao
                notification = Notification(
                    user_id=assignment.assigned_to,
                    title="Tin nhắn mới được giao",
                    message=f"Bạn có tin nhắn mới từ {customer.name}: {message_text[:50]}...",
                    type="message",
                    link=f"/staff/messages/{new_message.id}"
                )
                db.add(notification)
                db.commit()
                
                logger.info(f"Message {new_message.id} auto-assigned to user {assignment.assigned_to}")
            else:
                logger.warning(f"Could not auto-assign message {new_message.id}")
        
        return {"status": "success", "message": "Webhook processed"}
    
    except Exception as e:
        logger.error(f"Error processing Zalo webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )

@router.post("/meta")
async def meta_webhook(
    request: FastAPIRequest,
    db: Session = Depends(get_db)
):
    """
    Webhook nhận tin nhắn từ Meta (Facebook/Instagram)
    
    Đây là mock endpoint để demo. Trong production cần:
    - Verify webhook signature
    - Handle verification challenge
    - Parse Meta webhook format
    """
    
    try:
        data = await request.json()
        logger.info(f"Received Meta webhook: {data}")
        
        # Mock processing
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender_id = messaging.get("sender", {}).get("id")
                    message_data = messaging.get("message", {})
                    message_text = message_data.get("text", "")
                    message_id = message_data.get("mid")
                    
                    if not message_text:
                        continue
                    
                    # Tìm hoặc tạo customer
                    customer = db.query(Customer).filter(Customer.meta_id == sender_id).first()
                    if not customer:
                        customer = Customer(
                            meta_id=sender_id,
                            platform="facebook",
                            name=f"Khách hàng Facebook {sender_id}"
                        )
                        db.add(customer)
                        db.commit()
                        db.refresh(customer)
                    
                    # Tạo message
                    new_message = Message(
                        customer_id=customer.id,
                        content=message_text,
                        platform="facebook",
                        external_id=message_id,
                        direction="incoming",
                        status="pending"
                    )
                    db.add(new_message)
                    db.commit()
                    db.refresh(new_message)
                    
                    # Tự động giao việc
                    analyzer = KeywordAnalyzer(db)
                    assignment = analyzer.auto_assign_message(new_message)
                    
                    if assignment:
                        notification = Notification(
                            user_id=assignment.assigned_to,
                            title="Tin nhắn mới được giao",
                            message=f"Bạn có tin nhắn mới từ {customer.name}: {message_text[:50]}...",
                            type="message",
                            link=f"/staff/messages/{new_message.id}"
                        )
                        db.add(notification)
                        db.commit()
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing Meta webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )

@router.get("/meta")
async def meta_webhook_verification(
    request: FastAPIRequest
):
    """Verify Meta webhook"""
    
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    # Trong production, verify token với config
    if mode == "subscribe" and token == "mock-verify-token":
        return int(challenge)
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")

# Endpoint để test tạo tin nhắn thủ công (for demo)
@router.post("/test/create-message")
async def create_test_message(
    content: str,
    platform: str = "zalo",
    db: Session = Depends(get_db)
):
    """Tạo tin nhắn test để demo auto-assignment"""
    
    # Tạo customer test
    customer = Customer(
        name=f"Khách hàng test",
        platform=platform,
        phone="0900000000"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Tạo message
    new_message = Message(
        customer_id=customer.id,
        content=content,
        platform=platform,
        direction="incoming",
        status="pending"
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Tự động giao việc
    analyzer = KeywordAnalyzer(db)
    assignment = analyzer.auto_assign_message(new_message)
    
    if assignment:
        # Tạo thông báo
        notification = Notification(
            user_id=assignment.assigned_to,
            title="Tin nhắn mới được giao",
            message=f"Bạn có tin nhắn mới: {content[:50]}...",
            type="message",
            link=f"/staff/messages/{new_message.id}"
        )
        db.add(notification)
        db.commit()
        
        assigned_user = db.query(User).filter(User.id == assignment.assigned_to).first()
        
        return {
            "message_id": new_message.id,
            "assigned_to": assigned_user.full_name if assigned_user else None,
            "match_score": float(assignment.match_score),
            "notes": assignment.notes
        }
    else:
        return {
            "message_id": new_message.id,
            "assigned_to": None,
            "message": "Không tìm thấy nhân viên phù hợp"
        }
