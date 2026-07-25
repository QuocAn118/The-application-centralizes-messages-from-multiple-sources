from datetime import UTC, datetime

import pytest

from src.modules.inbox.domain.entities.attachment import Attachment
from src.modules.inbox.domain.entities.message import (
    InboundNeedsExternalIdError,
    Message,
    MessageDirection,
    OutboundNeedsSenderError,
)
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    EmptyMessageContentError,
    MessageContent,
)
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)


def _anh() -> AttachmentRef:
    return AttachmentRef(kind=AttachmentKind.IMAGE, url="https://x/a.jpg")


class TestMessageInbound:
    def test_tao_tin_den(self) -> None:
        ht = new_id()
        tin = Message.inbound(
            conversation_id=ht,
            content=MessageContent(text="Xin chào"),
            external_message_id="zalo_msg_1",
            now=BAY_GIO,
        )

        assert tin.direction is MessageDirection.INBOUND
        assert tin.conversation_id == ht
        assert tin.text == "Xin chào"
        assert tin.external_message_id == "zalo_msg_1"
        assert tin.sender_user_id is None

    def test_tin_den_bat_buoc_co_external_id(self) -> None:
        """external_message_id là chốt idempotency — thiếu là không chống trùng được."""
        with pytest.raises(InboundNeedsExternalIdError):
            Message.inbound(
                conversation_id=new_id(),
                content=MessageContent(text="Xin chào"),
                external_message_id="",
                now=BAY_GIO,
            )

    def test_tin_den_chi_co_attachment_khong_can_text(self) -> None:
        tin = Message.inbound(
            conversation_id=new_id(),
            content=MessageContent(attachments=(_anh(),)),
            external_message_id="msg_2",
            now=BAY_GIO,
        )

        assert tin.text is None

    def test_khong_tao_duoc_tin_rong(self) -> None:
        """Bất biến 'tin không rỗng' được giữ ở domain: rỗng thì MessageContent nổ."""
        with pytest.raises(EmptyMessageContentError):
            Message.inbound(
                conversation_id=new_id(),
                content=MessageContent(text="   "),
                external_message_id="msg_3",
                now=BAY_GIO,
            )


class TestMessageOutbound:
    def test_tao_tin_di(self) -> None:
        ht = new_id()
        nv = new_id()
        tin = Message.outbound(
            conversation_id=ht,
            content=MessageContent(text="Cảm ơn bạn"),
            sender_user_id=nv,
            now=BAY_GIO,
        )

        assert tin.direction is MessageDirection.OUTBOUND
        assert tin.sender_user_id == nv
        assert tin.external_message_id is None

    def test_tin_di_bat_buoc_co_nguoi_gui(self) -> None:
        """Tin đi phải biết ai gửi để ghi nhật ký và tính KPI sau này."""
        with pytest.raises(OutboundNeedsSenderError):
            Message.outbound(
                conversation_id=new_id(),
                content=MessageContent(text="Cảm ơn"),
                sender_user_id=None,  # type: ignore[arg-type]
                now=BAY_GIO,
            )


class TestAttachment:
    def test_tao_attachment_da_luu(self) -> None:
        tin_id = new_id()
        dinh_kem = Attachment.stored(
            message_id=tin_id,
            kind=AttachmentKind.IMAGE,
            stored_path="var/attachments/abc.jpg",
            original_url="https://cdn.zalo.me/abc.jpg",
            content_type="image/jpeg",
            size=12345,
            now=BAY_GIO,
        )

        assert dinh_kem.message_id == tin_id
        assert dinh_kem.kind is AttachmentKind.IMAGE
        assert dinh_kem.stored_path == "var/attachments/abc.jpg"
        assert dinh_kem.original_url == "https://cdn.zalo.me/abc.jpg"
        assert dinh_kem.size == 12345
