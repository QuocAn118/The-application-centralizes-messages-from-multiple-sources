"""Khoá hành vi: chuyển #2 sang chạy nền KHÔNG được làm chết #3.

Lỗi thật gặp 2026-09-15 (ngay sau khi bật hàng đợi): chuỗi hook ``post_ingest``
vốn dựa vào **thứ tự đăng ký** — #2 phân phòng trước, #3 đọc ``department_id``
rồi gán người. Khi #2 chuyển sang hàng đợi, hook #2 chỉ còn ``defer`` một job và
trả về sau vài mili-giây, nên lúc hook #3 chạy thì phòng vẫn ``NULL`` → #3 thoát
sớm, **không ai được gán, và không có lỗi nào hiện ra**.

Triệu chứng người dùng thấy: hội thoại về đúng phòng (worker làm được việc của
nó) nhưng cột người phụ trách trống vĩnh viễn.

Không test nào bắt được vì toàn bộ e2e chạy ``QUEUE_ENABLED=false`` — tức đường
đồng bộ cũ, nơi #3 vẫn hoạt động. Test này cố ý đi vào đường **nền**.

Cùng họ với lỗi NOT_ANALYZED hôm trước: một giả định ngầm bị phá trong im lặng.
"""

from uuid import UUID, uuid4

from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.ports import InboundEvent
from src.modules.inbox.domain.value_objects.message_content import MessageContent
from src.modules.inbox.domain.value_objects.platform import Platform

PHONG = uuid4()
NHAN_VIEN = uuid4()
HOI_THOAI = uuid4()


class _HoiThoai:
    """Bản ghi hội thoại tối thiểu mà hook #3 đọc."""

    def __init__(self) -> None:
        self.id = HOI_THOAI
        self.status = ConversationStatus.CHO_PHAN
        self.department_id: UUID | None = None
        self.assigned_user_id: UUID | None = None


class _TheGioi:
    """Trạng thái dùng chung giữa các bước, thay cho cơ sở dữ liệu.

    Đủ để diễn tả điều cần chứng minh: phòng được gán ở bước nào, và người phụ
    trách có được điền hay không.
    """

    def __init__(self) -> None:
        self.hoi_thoai = _HoiThoai()
        self.job_da_day: list[tuple[str, str]] = []

    def phan_phong(self) -> None:
        """Việc worker #2 làm: đưa hội thoại về một phòng và mở nó ra."""
        self.hoi_thoai.department_id = PHONG
        self.hoi_thoai.status = ConversationStatus.DANG_MO

    def gan_nguoi(self) -> None:
        self.hoi_thoai.assigned_user_id = NHAN_VIEN


def _su_kien() -> InboundEvent:
    return InboundEvent(
        platform=Platform.TELEGRAM,
        external_channel_id="bot1",
        external_customer_id="khach1",
        external_message_id="bot1:1",
        content=MessageContent(text="Cho toi gia"),
    )


_AUTO_ASSIGNED = "AUTO_ASSIGNED"
_AMBIGUOUS = "AMBIGUOUS"


class _SessionGia:
    """Session rỗng: ``chay_phan_tich`` chỉ mở/đóng và commit, không tự truy vấn."""

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, *a):  # type: ignore[no-untyped-def]
        return False

    async def commit(self) -> None:
        return None


def _bo_phu_thuoc_db(monkeypatch, *, outcome: str, department_id):  # type: ignore[no-untyped-def]
    """Cắt ``chay_phan_tich`` khỏi PostgreSQL và LLM, giữ nguyên luồng điều khiển.

    Chỉ thay hai điểm nối ngoài rìa — session factory và builder use case — nên
    phần được kiểm vẫn là code thật của ``chay_phan_tich``, gồm cả nhánh quyết
    định có đẩy job gán người hay không.
    """
    from datetime import UTC, datetime

    from src.jobs import wiring
    from src.modules.keyword.application.dto.keyword_dto import AnalysisView
    from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome

    ket_qua = AnalysisView(
        id=uuid4(),
        conversation_id=HOI_THOAI,
        outcome=AnalysisOutcome(outcome),
        extracted_terms=(),
        created_at=datetime(2026, 9, 15, tzinfo=UTC),
        suggested_department_id=department_id,
        confidence=None,
    )

    class _UseCaseGia:
        async def execute(self, conversation_id, force: bool = False):  # type: ignore[no-untyped-def]
            return ket_qua

    monkeypatch.setattr(wiring, "_lay_session_factory", lambda: _SessionGia)
    monkeypatch.setattr(
        "src.modules.keyword.infrastructure.inbox_bridge.analyze_factory."
        "build_analyze_conversation",
        lambda *a, **kw: _UseCaseGia(),
    )


def _hook_2_hang_doi(the_gioi: _TheGioi):  # type: ignore[no-untyped-def]
    """Hook #2 phiên bản HÀNG ĐỢI: chỉ đẩy job, không gọi LLM, không phân phòng."""

    async def hook(event: InboundEvent) -> None:
        the_gioi.job_da_day.append(("phan_tich_hoi_thoai", str(HOI_THOAI)))

    return hook


def _hook_3_hien_tai(the_gioi: _TheGioi):  # type: ignore[no-untyped-def]
    """Hook #3 y như code thật: chỉ gán khi ĐÃ có phòng và chưa ai nhận.

    Sao lại đúng điều kiện ở ``assignment/infrastructure/inbox_bridge/
    post_ingest_hook.py`` — đây chính là chỗ thoát sớm gây lỗi.
    """

    async def hook(event: InboundEvent) -> None:
        ht = the_gioi.hoi_thoai
        if (
            ht.status is not ConversationStatus.DANG_MO
            or ht.department_id is None
            or ht.assigned_user_id is not None
        ):
            return
        the_gioi.gan_nguoi()

    return hook


class TestChuoiHookDongBo:
    """Đường cũ (QUEUE_ENABLED=false) vẫn phải hoạt động — mốc so sánh."""

    async def test_chay_dong_bo_thi_gan_duoc_nguoi(self) -> None:
        the_gioi = _TheGioi()

        async def hook_2_dong_bo(event: InboundEvent) -> None:
            the_gioi.phan_phong()  # LLM chạy NGAY trong webhook

        for hook in (hook_2_dong_bo, _hook_3_hien_tai(the_gioi)):
            await hook(_su_kien())

        assert the_gioi.hoi_thoai.department_id == PHONG
        assert the_gioi.hoi_thoai.assigned_user_id == NHAN_VIEN


class TestChuoiHookChayNen:
    """Đường thật đang dùng (QUEUE_ENABLED=true) — chỗ lỗi nằm."""

    async def test_hook_3_khong_gan_duoc_vi_phong_chua_co(self) -> None:
        """Tái hiện lỗi: trong request, #3 chạy trước khi worker kịp phân phòng.

        Đây là hành vi ĐÚNG của riêng hook #3 (không có phòng thì không gán được)
        — lỗi nằm ở chỗ không còn ai gán người SAU khi worker phân phòng xong.
        """
        the_gioi = _TheGioi()

        for hook in (_hook_2_hang_doi(the_gioi), _hook_3_hien_tai(the_gioi)):
            await hook(_su_kien())

        assert the_gioi.job_da_day == [("phan_tich_hoi_thoai", str(HOI_THOAI))]
        assert the_gioi.hoi_thoai.department_id is None
        assert the_gioi.hoi_thoai.assigned_user_id is None

    async def test_job_phan_tich_phai_day_tiep_job_tu_gan(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """ĐÂY LÀ TEST KHOÁ LỖI.

        Gọi THẬT ``chay_phan_tich`` (đường chạy của worker) với use case giả trả
        về "đã phân phòng", rồi kiểm nó có đẩy tiếp job gán người hay không. Phải
        kiểm ở đây chứ không phải ở ``day_job_tu_gan``: lỗi không nằm ở chỗ hàm
        đẩy job hỏng, mà ở chỗ **không ai gọi nó**.

        Trước khi sửa: đỏ — phân phòng xong, chuỗi dừng, không ai gán người.
        Sau khi sửa: xanh.
        """
        from src.jobs import wiring

        da_day: list[UUID] = []

        async def day_gia(department_id, conversation_id=None, **kw):  # type: ignore[no-untyped-def]
            if department_id is not None and conversation_id is not None:
                da_day.append(conversation_id)

        _bo_phu_thuoc_db(monkeypatch, outcome=_AUTO_ASSIGNED, department_id=PHONG)
        monkeypatch.setattr(wiring, "day_job_tu_gan", day_gia)

        await wiring.chay_phan_tich(HOI_THOAI)

        assert da_day == [HOI_THOAI], (
            "Worker phân phòng xong PHẢI đẩy job tự gán — nếu không, "
            "hội thoại có phòng mà không bao giờ có người phụ trách"
        )

    async def test_khong_phan_duoc_phong_thi_khong_day_job_tu_gan(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """LLM không chọn được phòng (AMBIGUOUS) → không có phòng để chọn người."""
        from src.jobs import wiring

        da_day: list[UUID] = []

        async def day_gia(department_id, conversation_id=None, **kw):  # type: ignore[no-untyped-def]
            if department_id is not None and conversation_id is not None:
                da_day.append(conversation_id)

        _bo_phu_thuoc_db(monkeypatch, outcome=_AMBIGUOUS, department_id=None)
        monkeypatch.setattr(wiring, "day_job_tu_gan", day_gia)

        await wiring.chay_phan_tich(HOI_THOAI)

        assert da_day == []

    async def test_chuoi_day_du_ket_thuc_bang_mot_nguoi_phu_trach(self) -> None:
        """Toàn chuỗi, nhìn từ phía người dùng: tin đến → có người phụ trách.

        Ghép lại các mắt xích đã kiểm riêng ở trên để thấy kết cục cuối cùng.
        """
        the_gioi = _TheGioi()

        # 1. Request: đẩy job rồi trả 200. #3 chạy nhưng chưa có phòng để gán.
        for hook in (_hook_2_hang_doi(the_gioi), _hook_3_hien_tai(the_gioi)):
            await hook(_su_kien())
        assert the_gioi.hoi_thoai.assigned_user_id is None

        # 2. Worker chạy job phân tích: hội thoại có phòng.
        the_gioi.phan_phong()

        # 3. Worker chạy job gán người → hội thoại có người phụ trách.
        await _hook_3_hien_tai(the_gioi)(_su_kien())
        assert the_gioi.hoi_thoai.assigned_user_id == NHAN_VIEN


class TestKhongDayJobKhiChuaPhanDuocPhong:
    """Không phân được phòng thì đừng đẩy job gán — không có phòng để chọn người."""

    async def test_hoi_thoai_khong_co_phong_thi_khong_day_job(self) -> None:
        from src.jobs.wiring import day_job_tu_gan

        da_day: list[UUID] = []

        async def day_gia(conversation_id: UUID) -> None:
            da_day.append(conversation_id)

        await day_job_tu_gan(None, HOI_THOAI, _day=day_gia)
        assert da_day == []
