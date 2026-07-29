from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.modules.keyword.application.actor import ActorRole, KeywordActor
from src.modules.keyword.application.use_cases.analysis_read import (
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
