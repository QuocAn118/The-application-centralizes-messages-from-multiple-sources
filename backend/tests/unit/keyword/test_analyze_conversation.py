from datetime import UTC, datetime
from decimal import Decimal

from src.modules.keyword.application.use_cases.analyze_conversation import (
    AnalyzeConversation,
)
from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.ports import ConversationSnapshot
from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ClassificationResult,
    ExtractedTerm,
)
from src.shared.domain.identifiers import new_id
from tests.unit.keyword.fakes import (
    FakeAnalysisRepository,
    FakeClock,
    FakeConversationClassifier,
    FakeConversationDirectory,
    FakeConversationRouter,
    FakeKeywordRepository,
    FakeWorkforceDirectory,
)

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_BH = new_id()
PHONG_KD = new_id()
HT = new_id()


class _Boi:
    def __init__(self, *, is_awaiting=True, texts=("Sản phẩm bị lỗi",)) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.keyword_repo = FakeKeywordRepository(
            [
                Keyword.create(department_id=PHONG_BH, text="bảo hành", now=BAY_GIO),
                Keyword.create(department_id=PHONG_KD, text="báo giá", now=BAY_GIO),
            ]
        )
        self.analysis_repo = FakeAnalysisRepository()
        self.conv_dir = FakeConversationDirectory()
        self.conv_dir.set_snapshot(
            ConversationSnapshot(conversation_id=HT, is_awaiting=is_awaiting, first_texts=texts)
        )
        self.classifier = FakeConversationClassifier()
        self.router = FakeConversationRouter()
        self.workforce = FakeWorkforceDirectory()
        self.workforce.active_departments = {PHONG_BH, PHONG_KD}
        self.uc = AnalyzeConversation(
            keyword_repo=self.keyword_repo,
            analysis_repo=self.analysis_repo,
            conversation_directory=self.conv_dir,
            classifier=self.classifier,
            router=self.router,
            workforce=self.workforce,
            clock=self.clock,
        )

    def _terms(self):
        return (ExtractedTerm(text="lỗi", normalized="loi"),)


class TestTuPhan:
    async def test_llm_chon_phong_hop_le_du_tin_cay_thi_tu_phan(self) -> None:
        bc = _Boi()
        bc.classifier.set_result(
            ClassificationResult(
                department_id=PHONG_BH, confidence=Decimal("0.9"), terms=bc._terms()
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AUTO_ASSIGNED
        assert view.suggested_department_id == PHONG_BH
        assert bc.router.assigned == [(HT, PHONG_BH)]
        # Danh mục 2 phòng được bơm cho LLM.
        assert len(bc.classifier.departments_seen[0]) == 2

    async def test_tin_cay_thap_giu_cho_phan(self) -> None:
        bc = _Boi()
        bc.classifier.set_result(
            ClassificationResult(
                department_id=PHONG_BH, confidence=Decimal("0.3"), terms=bc._terms()
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS
        assert bc.router.assigned == []
        assert len(view.extracted_terms) == 1

    async def test_llm_khong_chon_phong_giu_cho_phan(self) -> None:
        bc = _Boi()
        bc.classifier.set_result(
            ClassificationResult(department_id=None, confidence=Decimal("0.2"), terms=bc._terms())
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS
        assert bc.router.assigned == []

    async def test_llm_bia_phong_khong_ton_tai_giu_cho_phan(self) -> None:
        # Code gác: LLM trả phòng không nằm trong danh mục/không active -> không phân.
        bc = _Boi()
        phong_la = new_id()
        bc.classifier.set_result(
            ClassificationResult(
                department_id=phong_la, confidence=Decimal("0.95"), terms=bc._terms()
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS
        assert bc.router.assigned == []

    async def test_phan_that_bai_giu_cho_phan(self) -> None:
        bc = _Boi()
        bc.router.succeed = False
        bc.classifier.set_result(
            ClassificationResult(
                department_id=PHONG_BH, confidence=Decimal("0.9"), terms=bc._terms()
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS


class TestNuotLoiLLM:
    async def test_llm_loi_khong_nem_ra_ngoai(self) -> None:
        bc = _Boi()
        bc.classifier.raise_error = True

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.NOT_ANALYZED
        assert view.extracted_terms == ()
        assert bc.router.assigned == []


class TestGuardLap:
    async def test_da_phan_tich_thi_bo_qua(self) -> None:
        bc = _Boi()
        bc.classifier.set_result(
            ClassificationResult(department_id=None, confidence=Decimal("0.2"), terms=bc._terms())
        )
        await bc.uc.execute(HT)
        so_lan_1 = len(bc.classifier.calls)

        # Lần hai: đã có bản ghi -> bỏ qua, không gọi LLM lại.
        view = await bc.uc.execute(HT)

        assert view is None
        assert len(bc.classifier.calls) == so_lan_1

    async def test_force_phan_tich_lai(self) -> None:
        bc = _Boi()
        bc.classifier.set_result(
            ClassificationResult(department_id=None, confidence=Decimal("0.2"), terms=bc._terms())
        )
        await bc.uc.execute(HT)

        view = await bc.uc.execute(HT, force=True)

        assert view is not None
        assert len(bc.classifier.calls) == 2


class TestBoQua:
    async def test_khong_phai_cho_phan_bo_qua(self) -> None:
        bc = _Boi(is_awaiting=False)

        view = await bc.uc.execute(HT)

        assert view is None
        assert bc.classifier.calls == []

    async def test_khong_co_tin_bo_qua(self) -> None:
        bc = _Boi(texts=())

        view = await bc.uc.execute(HT)

        assert view is None
        assert bc.classifier.calls == []

    async def test_hoi_thoai_khong_ton_tai_bo_qua(self) -> None:
        bc = _Boi()

        view = await bc.uc.execute(new_id())

        assert view is None
