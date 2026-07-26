"""WebSocket endpoint cho tín hiệu realtime của inbox.

Client kết nối ``/ws/inbox?token=<access_token>``; server xác thực, đăng ký vào
notifier theo phạm vi quyền, rồi giữ kết nối. Chỉ đẩy tín hiệu, không nội dung.
"""

import logging

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from src.modules.inbox.application.actor import ActorRole, InboxActor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/inbox")
async def ws_inbox(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)  # policy violation
        return

    actor = await _xac_thuc(websocket, token)
    if actor is None:
        await websocket.close(code=1008)
        return

    notifier = websocket.app.state.inbox_notifier
    ket_noi = await notifier.connect(websocket, actor)
    try:
        while True:
            # Kênh một chiều: chỉ chờ client rớt; mọi tin client gửi lên bị bỏ.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await notifier.disconnect(ket_noi)


async def _xac_thuc(websocket: WebSocket, token: str) -> InboxActor | None:
    """Giải mã token + kiểm nhân viên còn hoạt động, trả InboxActor trung lập."""
    try:
        payload = websocket.app.state.token_service.decode_access_token(token)
    except Exception:
        return None

    session_factory = websocket.app.state.session_factory
    directory_factory = websocket.app.state.inbox_directory_factory
    async with session_factory() as session:
        agent = await directory_factory(session).get_agent(payload.user_id)
    if agent is None or not agent.is_active:
        return None
    return InboxActor(
        user_id=agent.user_id,
        role=ActorRole(agent.role),
        department_id=agent.department_id,
    )
