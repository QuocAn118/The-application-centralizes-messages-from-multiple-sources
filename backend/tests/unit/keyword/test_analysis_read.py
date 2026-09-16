from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.modules.keyword.application.actor import ActorRole, KeywordActor
from src.modules.keyword.application.use_cases.analysis_read import (
    BaoDamKichHoatPhanTichDuoc,
    GetConversationAnalyses,
    ListConversationAnalyses,
)
from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.value_objects.extracted_term import ExtractedTerm
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.keyword.fakes import FakeAnalysisRepository

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_A = new_id()
PHONG_B = new_id()


def _admin() -> KeywordActor:
    return KeywordActor(user_id=new_id(), role=ActorRole.ADMIN, department_id=None)


def _staff(department_id=PHONG_A) -> KeywordActor:
    return KeywordActor(user_id=new_id(), role=ActorRole.STAFF, department_id=department_id)


def _phan_tich(conversation_id, department_id) -> ConversationAnalysis:
    return ConversationAnalysis.auto_assigned(
        conversation_id=conversation_id,
        extracted_terms=(ExtractedTerm(text="x", normalized="x"),),
        department_id=department_id,
        confidence=Decimal("0.9"),
        now=BAY_GIO,
    )


class TestList:
    async def test_admin_thay_tat_ca(self) -> None:
        repo = FakeAnalysisRepository()
        await repo.add(_phan_tich(new_id(), PHONG_A))
        await repo.add(_phan_tich(new_id(), PHONG_B))

        page = await ListConversationAnalyses(repo).execute(_admin())
        assert page.total == 2

    async def test_staff_chi_thay_phong_minh(self) -> None:
        repo = FakeAnalysisRepository()
        await repo.add(_phan_tich(new_id(), PHONG_A))
        await repo.add(_phan_tich(new_id(), PHONG_B))

        page = await ListConversationAnalyses(repo).execute(_staff(PHONG_A))
        assert page.total == 1
        assert page.items[0].suggested_department_id == PHONG_A


class TestGet:
    async def test_xem_lich_su_cua_hoi_thoai(self) -> None:
        repo = FakeAnalysisRepository()
        ht = new_id()
        await repo.add(_phan_tich(ht, PHONG_A))

        views = await GetConversationAnalyses(repo).execute(_staff(PHONG_A), ht)
        assert len(views) == 1

    async def test_staff_phong_khac_bi_tu_choi(self) -> None:
        repo = FakeAnalysisRepository()
        ht = new_id()
        await repo.add(_phan_tich(ht, PHONG_A))

        with pytest.raises(PermissionDeniedError):
            await GetConversationAnalyses(repo).execute(_staff(PHONG_B), ht)

    async def test_khong_ton_tai(self) -> None:
        repo = FakeAnalysisRepository()
        with pytest.raises(NotFoundError):
            await GetConversationAnalyses(repo).execute(_admin(), new_id())


def _manager(department_id=PHONG_A) -> KeywordActor:
    return KeywordActor(user_id=new_id(), role=ActorRole.MANAGER, department_id=department_id)


class TestBaoDamKichHoatPhanTichDuoc:
    """Nợ N5 — đường GHI phải chặt bằng đường ĐỌC.

    Đo thật trước khi sửa: Manager **GET** phân tích của hội thoại phòng khác
    nhận **403**, nhưng **POST** kích hoạt lại chính hội thoại đó nhận **200**.
    Ghi ở đây nghĩa là gọi LLM (tốn tiền) và có thể định tuyến lại hội thoại của
    phòng khác.
    """

    async def test_manager_phong_khac_bi_tu_choi(self) -> None:
        # Đây là lỗ hổng N5: trước khi sửa, lời gọi này KHÔNG ném gì cả.
        repo = FakeAnalysisRepository()
        ht = new_id()
        await repo.add(_phan_tich(ht, PHONG_A))

        with pytest.raises(PermissionDeniedError):
            await BaoDamKichHoatPhanTichDuoc(repo).execute(_manager(PHONG_B), ht)

    async def test_manager_dung_phong_thi_duoc(self) -> None:
        repo = FakeAnalysisRepository()
        ht = new_id()
        await repo.add(_phan_tich(ht, PHONG_A))

        await BaoDamKichHoatPhanTichDuoc(repo).execute(_manager(PHONG_A), ht)

    async def test_admin_lam_duoc_moi_hoi_thoai(self) -> None:
        repo = FakeAnalysisRepository()
        ht = new_id()
        await repo.add(_phan_tich(ht, PHONG_B))

        await BaoDamKichHoatPhanTichDuoc(repo).execute(_admin(), ht)

    async def test_hoi_thoai_chua_phan_tich_lan_nao_thi_ai_cung_duoc(self) -> None:
        # Quan trọng: KHÔNG được chặn ca này. Hội thoại chưa có bản ghi nào
        # nghĩa là còn CHO_PHAN — chưa thuộc phòng nào nên không có gì để xâm
        # phạm, và đây chính là trường hợp dùng chính đáng (Manager vừa thêm từ
        # khoá, muốn AI thử phân lại hàng chờ chung). Chặn ở đây là sửa quá tay,
        # biến bản vá quyền thành một lỗi chức năng.
        repo = FakeAnalysisRepository()
        await BaoDamKichHoatPhanTichDuoc(repo).execute(_manager(PHONG_A), new_id())

    async def test_khop_dung_quy_tac_cua_get(self) -> None:
        # Hai đường phải cùng kết luận trên cùng dữ liệu: lệch nhau là mầm mống
        # của đúng lỗi N5 lần sau.
        repo = FakeAnalysisRepository()
        ht = new_id()
        await repo.add(_phan_tich(ht, PHONG_A))
        actor = _manager(PHONG_B)

        with pytest.raises(PermissionDeniedError):
            await GetConversationAnalyses(repo).execute(actor, ht)
        with pytest.raises(PermissionDeniedError):
            await BaoDamKichHoatPhanTichDuoc(repo).execute(actor, ht)
