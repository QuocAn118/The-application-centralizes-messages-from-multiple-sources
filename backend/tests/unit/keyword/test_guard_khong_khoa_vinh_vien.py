"""Khoá hành vi: LLM lỗi một lần KHÔNG được khoá hội thoại vĩnh viễn.

Lỗi thật gặp 2026-09-15: model Gemini (`gemini-2.0-flash`) bị Google gỡ → mọi
lời gọi trả 404 → use case ghi ``NOT_ANALYZED`` → guard RB-5 coi đó là "đã phân
tích" → **mọi tin sau đó không bao giờ được phân tích nữa**, và không có lỗi nào
hiện ra. Hội thoại nằm mãi ở CHO_PHAN, job báo "Success" trong 0.035 giây.

Đây là loại lỗi tệ nhất: im lặng, và tự khoá chính nó lại.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.modules.keyword.application.use_cases.analyze_conversation import (
    AnalyzeConversation,
)
from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.ports import ClassifierError, ConversationSnapshot
from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ClassificationResult,
    ExtractedTerm,
)

BAY_GIO = datetime(2026, 9, 15, 10, 0, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return BAY_GIO


class _Directory:
    """Hội thoại CHO_PHAN, có hai tin của khách."""

    def __init__(self, conversation_id):  # type: ignore[no-untyped-def]
        self._id = conversation_id

    async def get_snapshot(self, conversation_id, max_messages):  # type: ignore[no-untyped-def]
        return ConversationSnapshot(
            conversation_id=self._id,
            is_awaiting=True,
            first_texts=("Giá", "Cho tôi giá"),
        )


class _AnalysisRepo:
    def __init__(self, ban_dau=()):  # type: ignore[no-untyped-def]
        self.items: list[ConversationAnalysis] = list(ban_dau)

    async def add(self, analysis: ConversationAnalysis) -> None:
        self.items.append(analysis)

    async def list_for_conversation(self, conversation_id):  # type: ignore[no-untyped-def]
        return [a for a in self.items if a.conversation_id == conversation_id]


class _KeywordRepo:
    def __init__(self, items=()):  # type: ignore[no-untyped-def]
        self._items = list(items)

    async def list_all_active(self):  # type: ignore[no-untyped-def]
        return self._items


class _Router:
    def __init__(self) -> None:
        self.da_gan: list[tuple] = []

    async def assign_to_department(self, conversation_id, department_id) -> bool:  # type: ignore[no-untyped-def]
        self.da_gan.append((conversation_id, department_id))
        return True


class _Workforce:
    async def department_exists_active(self, department_id) -> bool:  # type: ignore[no-untyped-def]
        return True


class _ClassifierLoi:
    """Mô phỏng LLM hỏng (model 404, mạng chập, quota)."""

    def __init__(self) -> None:
        self.so_lan_goi = 0

    async def classify(self, texts, departments):  # type: ignore[no-untyped-def]
        self.so_lan_goi += 1
        raise ClassifierError("Gọi Gemini lỗi HTTP 404.")


class _ClassifierTot:
    """LLM chạy được, chọn một phòng với độ tin cậy cao."""

    def __init__(self, department_id) -> None:  # type: ignore[no-untyped-def]
        self.department_id = department_id
        self.so_lan_goi = 0

    async def classify(self, texts, departments):  # type: ignore[no-untyped-def]
        self.so_lan_goi += 1
        return ClassificationResult(
            department_id=self.department_id,
            confidence=Decimal("0.9"),
            terms=(ExtractedTerm(text="hỏi giá", normalized="hoi gia"),),
        )


def _use_case(classifier, analysis_repo, router=None):  # type: ignore[no-untyped-def]
    conversation_id = uuid4()
    return (
        AnalyzeConversation(
            keyword_repo=_KeywordRepo(),
            analysis_repo=analysis_repo,
            conversation_directory=_Directory(conversation_id),
            classifier=classifier,
            router=router or _Router(),
            workforce=_Workforce(),
            clock=_Clock(),
        ),
        conversation_id,
    )


class TestKhongKhoaVinhVien:
    async def test_ban_ghi_not_analyzed_khong_chan_lan_phan_tich_sau(self) -> None:
        """Đây là lỗi gốc: NOT_ANALYZED là trạng thái TẠM, không phải kết luận."""
        repo = _AnalysisRepo()
        classifier_loi = _ClassifierLoi()
        uc, cid = _use_case(classifier_loi, repo)

        # Lần 1: LLM hỏng → ghi NOT_ANALYZED.
        await uc.execute(cid)
        assert classifier_loi.so_lan_goi == 1
        assert len(repo.items) == 1
        assert repo.items[0].outcome is AnalysisOutcome.NOT_ANALYZED

        # Lần 2 (LLM đã sửa): PHẢI gọi lại LLM, không được bỏ qua.
        phong = uuid4()
        classifier_tot = _ClassifierTot(phong)
        router = _Router()
        uc2 = AnalyzeConversation(
            keyword_repo=_KeywordRepo(),
            analysis_repo=repo,
            conversation_directory=_Directory(cid),
            classifier=classifier_tot,
            router=router,
            workforce=_Workforce(),
            clock=_Clock(),
        )
        kq = await uc2.execute(cid)

        assert classifier_tot.so_lan_goi == 1, "LLM phải được gọi lại sau lần lỗi"
        assert kq is not None
        assert kq.outcome is AnalysisOutcome.AUTO_ASSIGNED
        assert router.da_gan == [(cid, phong)]

    async def test_phan_tich_thanh_cong_that_thi_van_chan_goi_lai(self) -> None:
        """Guard RB-5 vẫn phải giữ: đã phân tích THẬT rồi thì không gọi LLM nữa.

        Sửa lỗi trên không được làm mất tác dụng tiết kiệm token của RB-5.
        """
        phong = uuid4()
        repo = _AnalysisRepo()
        classifier = _ClassifierTot(phong)
        uc, cid = _use_case(classifier, repo)

        await uc.execute(cid)
        assert classifier.so_lan_goi == 1

        # Lần hai: đã có bản ghi AUTO_ASSIGNED → bỏ qua, KHÔNG gọi LLM.
        kq2 = await uc.execute(cid)
        assert kq2 is None
        assert classifier.so_lan_goi == 1, "Không được gọi LLM lại khi đã phân tích thật"

    async def test_ban_ghi_ambiguous_cung_chan_goi_lai(self) -> None:
        """AMBIGUOUS cũng là kết quả THẬT (LLM chạy được, chỉ không đủ chắc)."""
        repo = _AnalysisRepo(
            [
                ConversationAnalysis.ambiguous(
                    conversation_id=uuid4(),
                    extracted_terms=(ExtractedTerm(text="a", normalized="a"),),
                    confidence=Decimal("0.2"),
                    now=BAY_GIO,
                )
            ]
        )
        # Gắn bản ghi vào đúng conversation của use case.
        classifier = _ClassifierTot(uuid4())
        uc, cid = _use_case(classifier, repo)
        repo.items[0] = ConversationAnalysis.ambiguous(
            conversation_id=cid,
            extracted_terms=(ExtractedTerm(text="a", normalized="a"),),
            confidence=Decimal("0.2"),
            now=BAY_GIO,
        )

        kq = await uc.execute(cid)
        assert kq is None
        assert classifier.so_lan_goi == 0, "AMBIGUOUS là kết quả thật, không gọi lại"

    async def test_force_van_goi_lai_du_da_phan_tich(self) -> None:
        """Manager kích hoạt lại thủ công thì bỏ qua mọi guard."""
        phong = uuid4()
        repo = _AnalysisRepo()
        classifier = _ClassifierTot(phong)
        uc, cid = _use_case(classifier, repo)

        await uc.execute(cid)
        await uc.execute(cid, force=True)
        assert classifier.so_lan_goi == 2


@pytest.mark.parametrize("so_lan_loi", [1, 3])
class TestLoiLapLai:
    async def test_nhieu_lan_loi_lien_tiep_van_thu_lai_duoc(self, so_lan_loi: int) -> None:
        """LLM hỏng nhiều lần liên tiếp vẫn không khoá vĩnh viễn hội thoại."""
        repo = _AnalysisRepo()
        classifier = _ClassifierLoi()
        uc, cid = _use_case(classifier, repo)

        for _ in range(so_lan_loi):
            await uc.execute(cid)

        assert classifier.so_lan_goi == so_lan_loi
        assert all(a.outcome is AnalysisOutcome.NOT_ANALYZED for a in repo.items)
