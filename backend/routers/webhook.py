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
import os
import requests
import json

# Lấy token từ biến môi trường
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_telegram_message(chat_id: str, text: str):
    """
    Gửi tin nhắn đến user trên Telegram
    """
    if not TELEGRAM_BOT_TOKEN or "YOUR_TELEGRAM_BOT_TOKEN_HERE" in TELEGRAM_BOT_TOKEN:
        logger.error("Telegram Bot Token chưa được cấu hình")
        return None
        
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None

@router.post("/telegram")
async def telegram_webhook(request: FastAPIRequest, db: Session = Depends(get_db)):
    """
    Nhận tin nhắn từ Telegram Bot
    """
    try:
        data = await request.json()
        logger.info(f"Received Telegram Webhook: {json.dumps(data)}")
        
        # Kiểm tra cấu trúc tin nhắn
        if "message" not in data:
            return {"status": "ok", "message": "No message data"}
        
        message_data = data["message"]
        
        # Lấy thông tin người gửi
        from_user = message_data.get("from", {})
        chat = message_data.get("chat", {})
        text = message_data.get("text", "")
        
        # Bỏ qua tin nhắn không có text (ví dụ sticker, hình ảnh chưa hỗ trợ)
        if not text:
            return {"status": "ok", "message": "No text content"}
            
        telegram_id = str(from_user.get("id"))
        chat_id = str(chat.get("id"))
        
        # Xử lý lệnh /start
        if text == "/start":
            send_telegram_message(
                chat_id,
                "👋 <b>Xin chào!</b> Tôi là OmniChat Support Bot.\n\nHãy gửi câu hỏi của bạn, chúng tôi sẽ chuyển đến nhân viên hỗ trợ ngay lập tức!"
            )
            return {"status": "ok"}
        
        # 1. Tìm hoặc tạo Customer
        customer = db.query(Customer).filter(
            Customer.platform == "telegram",
            Customer.meta_id == telegram_id
        ).first()
        
        if not customer:
            username = from_user.get("username", "")
            first_name = from_user.get("first_name", "")
            last_name = from_user.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = username or f"Telegram User {telegram_id}"
                
            customer = Customer(
                name=full_name,
                platform="telegram",
                meta_id=telegram_id,
                email=f"{username}@telegram.user" if username else None,
                city="Unknown",
                zalo_id=None # Đảm bảo không conflict
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            logger.info(f"Created new customer: {full_name} ({telegram_id})")
        
        # 2. Lưu tin nhắn vào database
        new_message = Message(
            customer_id=customer.id,
            content=text,
            platform="telegram",
            external_id=str(message_data.get("message_id")),
            direction="incoming",
            status="pending"
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        logger.info(f"Saved message {new_message.id} from customer {customer.id}")
        
        # 3. Tự động phân công tin nhắn
        analyzer = KeywordAnalyzer(db)
        # Lưu ý: auto_assign_message nhận Message object và tự commit
        assignment = analyzer.auto_assign_message(new_message)
        
        if assignment:
            # Lấy thông tin staff được gán để reply chuyên nghiệp hơn (optional)
            # Hiện tại chỉ reply chung
            send_telegram_message(
                chat_id,
                "✅ Cảm ơn bạn! Tin nhắn của bạn đã được chuyển đến bộ phận hỗ trợ.\nNhân viên của chúng tôi sẽ phản hồi sớm nhất có thể."
            )
            return {
                "status": "success",
                "message_id": new_message.id,
                "assigned_to": assignment.assigned_to
            }
        else:
            send_telegram_message(
                chat_id,
                "✅ Cảm ơn bạn! Chúng tôi đã nhận được tin nhắn và sẽ liên hệ lại sớm."
            )
            return {
                "status": "pending",
                "message_id": new_message.id,
                "message": "No matching staff found"
            }
            
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        # Không raise error để Telegram không retry spam
        return {"status": "error", "detail": str(e)}

@router.post("/telegram/send")
async def send_message_to_telegram(
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    API để staff gửi tin nhắn phản hồi đến khách hàng qua Telegram
    Payload: { "customer_id": int, "message": str }
    """
    customer_id = payload.get("customer_id")
    message_content = payload.get("message")
    
    if not customer_id or not message_content:
        raise HTTPException(status_code=400, detail="Missing customer_id or message")
        
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    if customer.platform != "telegram" or not customer.meta_id:
        raise HTTPException(status_code=400, detail="Customer is not a Telegram user")
    
    # Gửi tin nhắn qua API Telegram
    result = send_telegram_message(customer.meta_id, message_content)
    
    if result and result.get("ok"):
        # Lưu tin nhắn outgoing vào database
        new_message = Message(
            customer_id=customer_id,
            content=message_content,
            platform="telegram",
            direction="outgoing",
            status="completed" # Đánh dấu là đã xử lý/trả lời
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        return {"status": "success", "result": result}
    else:
        logger.error(f"Failed to send Telegram message: {result}")
        raise HTTPException(status_code=500, detail="Failed to send message to Telegram API")
