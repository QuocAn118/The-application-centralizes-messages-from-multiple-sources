from datetime import UTC, datetime

import pytest

from src.modules.inbox.domain.entities.conversation import (
    AlreadyAssignedError,
    Conversation,
    ConversationStatus,
    NotAwaitingAssignmentError,
    NotOpenError,
)
from src.shared.domain.identifiers import new_id

BAY_GIO = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
SAU_5_PHUT = datetime(2026, 7, 24, 10, 5, tzinfo=UTC)


def _tao_cho_phan() -> Conversation:
    """Hội thoại từ kênh chưa gắn phòng → CHO_PHAN."""
    return Conversation.start(
        channel_id=new_id(),
        customer_id=new_id(),
        department_id=None,
        now=BAY_GIO,
    )


def _tao_dang_mo() -> Conversation:
    """Hội thoại từ kênh đã gắn phòng → DANG_MO ngay."""
    return Conversation.start(
        channel_id=new_id(),
        customer_id=new_id(),
        department_id=new_id(),
        now=BAY_GIO,
    )


class TestKhoiTao:
    def test_kenh_chua_gan_phong_thi_cho_phan(self) -> None:
        ht = _tao_cho_phan()

        assert ht.status is ConversationStatus.CHO_PHAN
        assert ht.department_id is None
        assert ht.assigned_user_id is None

    def test_kenh_da_gan_phong_thi_dang_mo(self) -> None:
        phong = new_id()
        ht = Conversation.start(
            channel_id=new_id(),
            customer_id=new_id(),
            department_id=phong,
            now=BAY_GIO,
        )

        assert ht.status is ConversationStatus.DANG_MO
        assert ht.department_id == phong


class TestPhanPhong:
    def test_phan_tu_cho_phan_sang_dang_mo(self) -> None:
        ht = _tao_cho_phan()
        phong = new_id()

        ht.assign_to_department(phong, now=SAU_5_PHUT)

        assert ht.status is ConversationStatus.DANG_MO
        assert ht.department_id == phong
        assert ht.updated_at == SAU_5_PHUT

    def test_khong_phan_duoc_khi_da_dang_mo(self) -> None:
        """Đã thuộc phòng rồi thì đổi phòng là chuyện khác, không phải 'phân'."""
        ht = _tao_dang_mo()

        with pytest.raises(NotAwaitingAssignmentError):
            ht.assign_to_department(new_id(), now=SAU_5_PHUT)


class TestNhanVaDong:
    def test_nhan_hoi_thoai(self) -> None:
        ht = _tao_dang_mo()
        nv = new_id()

        ht.assign_to_agent(nv, now=SAU_5_PHUT)

        assert ht.assigned_user_id == nv

    def test_khong_nhan_duoc_khi_con_cho_phan(self) -> None:
        """Chưa thuộc phòng thì chưa ai nhận được — phải phân phòng trước."""
        ht = _tao_cho_phan()

        with pytest.raises(NotOpenError):
            ht.assign_to_agent(new_id(), now=SAU_5_PHUT)

    def test_khong_nhan_de_khi_da_co_nguoi(self) -> None:
        ht = _tao_dang_mo()
        ht.assign_to_agent(new_id(), now=SAU_5_PHUT)

        with pytest.raises(AlreadyAssignedError):
            ht.assign_to_agent(new_id(), now=SAU_5_PHUT)

    def test_dong_hoi_thoai(self) -> None:
        ht = _tao_dang_mo()

        ht.close(now=SAU_5_PHUT)

        assert ht.status is ConversationStatus.DA_DONG
        assert ht.closed_at == SAU_5_PHUT  # mốc đóng chính xác

    def test_khong_dong_duoc_khi_con_cho_phan(self) -> None:
        ht = _tao_cho_phan()

        with pytest.raises(NotOpenError):
            ht.close(now=SAU_5_PHUT)


class TestTinDenVaMoLai:
    def test_tin_moi_cap_nhat_moc_thoi_gian(self) -> None:
        ht = _tao_dang_mo()

        ht.register_incoming(now=SAU_5_PHUT)

        assert ht.last_message_at == SAU_5_PHUT

    def test_tin_moi_khi_da_dong_thi_mo_lai(self) -> None:
        ht = _tao_dang_mo()
        ht.close(now=SAU_5_PHUT)

        ht.register_incoming(now=SAU_5_PHUT)

        assert ht.status is ConversationStatus.DANG_MO
        assert ht.closed_at is None  # mở lại xoá mốc đóng

    def test_tin_moi_khi_cho_phan_van_giu_cho_phan(self) -> None:
        """Khách nhắn thêm khi đang chờ phân không tự đẩy sang DANG_MO."""
        ht = _tao_cho_phan()

        ht.register_incoming(now=SAU_5_PHUT)

        assert ht.status is ConversationStatus.CHO_PHAN

    def test_tin_den_tre_khong_keo_moc_thoi_gian_lui(self) -> None:
        """Webhook đến trễ (now cũ hơn last_message_at) không được kéo mốc lùi."""
        ht = _tao_dang_mo()
        ht.register_incoming(now=SAU_5_PHUT)

        truoc_do = datetime(2026, 7, 24, 9, 0, tzinfo=UTC)
        ht.register_incoming(now=truoc_do)

        assert ht.last_message_at == SAU_5_PHUT

    def test_mo_lai_giu_nguyen_nguoi_da_gan(self) -> None:
        """Đóng rồi mở lại vẫn thuộc người cũ — không bắt nhận lại từ đầu."""
        ht = _tao_dang_mo()
        nv = new_id()
        ht.assign_to_agent(nv, now=SAU_5_PHUT)
        ht.close(now=SAU_5_PHUT)

        ht.register_incoming(now=SAU_5_PHUT)

        assert ht.assigned_user_id == nv
