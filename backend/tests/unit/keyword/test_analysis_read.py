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
from src.modules.keyword.domain.ports import ConversationSnapshot
from src.modules.keyword.domain.value_objects.extracted_term import ExtractedTerm
from src.shared.application.exceptions import NotFoundError, PermissionDeniedError
from src.shared.domain.identifiers import new_id
from tests.unit.keyword.fakes import FakeAnalysisRepository, FakeConversationDirectory

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
    """Quyền phân tích lại xét theo phòng HIỆN TẠI của hội thoại, không theo bản
    ghi phân tích (bản N5 cũ chặn nhầm hội thoại chờ phân đã có bản ghi)."""

    @staticmethod
    def _thu_muc(ht, department_id) -> FakeConversationDirectory:
        d = FakeConversationDirectory()
        d.set_snapshot(
            ConversationSnapshot(
                conversation_id=ht,
                is_awaiting=department_id is None,
                first_texts=("x",),
                department_id=department_id,
            )
        )
        return d

    async def test_hoi_thoai_phong_khac_bi_tu_choi(self) -> None:
        ht = new_id()
        with pytest.raises(PermissionDeniedError):
            await BaoDamKichHoatPhanTichDuoc(self._thu_muc(ht, PHONG_A)).execute(
                _manager(PHONG_B), ht
            )

    async def test_manager_dung_phong_thi_duoc(self) -> None:
        ht = new_id()
        await BaoDamKichHoatPhanTichDuoc(self._thu_muc(ht, PHONG_A)).execute(_manager(PHONG_A), ht)

    async def test_admin_lam_duoc_moi_hoi_thoai(self) -> None:
        ht = new_id()
        await BaoDamKichHoatPhanTichDuoc(self._thu_muc(ht, PHONG_B)).execute(_admin(), ht)

    async def test_cho_phan_thi_manager_nao_cung_duoc(self) -> None:
        # Kể cả khi đã có bản ghi NOT_ANALYZED / AMBIGUOUS nghiêng về phòng khác —
        # guard không đọc bản ghi phân tích nữa, chỉ đọc phòng hiện tại.
        ht = new_id()
        await BaoDamKichHoatPhanTichDuoc(self._thu_muc(ht, None)).execute(_manager(PHONG_B), ht)

    async def test_khong_co_hoi_thoai_thi_cho_qua(self) -> None:
        # Use case phía sau trả None (200) như trước.
        await BaoDamKichHoatPhanTichDuoc(FakeConversationDirectory()).execute(
            _manager(PHONG_A), new_id()
        )
