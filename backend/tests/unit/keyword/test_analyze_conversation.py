from datetime import UTC, datetime
from decimal import Decimal

from src.modules.keyword.application.use_cases.analyze_conversation import (
    AnalyzeConversation,
)
from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.ports import ConversationSnapshot
from src.modules.keyword.domain.value_objects.extracted_term import (
    AnalysisOutcome,
    ExtractedTerm,
    ExtractionResult,
)
from src.shared.domain.identifiers import new_id
from tests.unit.keyword.fakes import (
    FakeAnalysisRepository,
    FakeClock,
    FakeConversationDirectory,
    FakeConversationRouter,
    FakeKeywordExtractor,
    FakeKeywordRepository,
)

BAY_GIO = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
PHONG_BH = new_id()
PHONG_KD = new_id()
HT = new_id()


def _kq(*terms_conf) -> ExtractionResult:
    terms, conf = terms_conf
    return ExtractionResult(terms=terms, confidence=conf)


class _Boi:
    def __init__(self, *, is_awaiting=True, texts=("Sản phẩm bị lỗi",)) -> None:
        self.clock = FakeClock(BAY_GIO)
        self.keyword_repo = FakeKeywordRepository(
            [
                Keyword.create(department_id=PHONG_BH, text="bảo hành", now=BAY_GIO),
                Keyword.create(department_id=PHONG_BH, text="lỗi", now=BAY_GIO),
                Keyword.create(department_id=PHONG_KD, text="báo giá", now=BAY_GIO),
            ]
        )
        self.analysis_repo = FakeAnalysisRepository()
        self.conv_dir = FakeConversationDirectory()
        self.conv_dir.set_snapshot(
            ConversationSnapshot(conversation_id=HT, is_awaiting=is_awaiting, first_texts=texts)
        )
        self.extractor = FakeKeywordExtractor()
        self.router = FakeConversationRouter()
        self.uc = AnalyzeConversation(
            keyword_repo=self.keyword_repo,
            analysis_repo=self.analysis_repo,
            conversation_directory=self.conv_dir,
            extractor=self.extractor,
            router=self.router,
            clock=self.clock,
        )


class TestTuPhan:
    async def test_khop_mot_phong_du_tin_cay_thi_tu_phan(self) -> None:
        bc = _Boi()
        bc.extractor.set_result(
            ExtractionResult(
                terms=(ExtractedTerm(text="lỗi bảo hành", normalized="loi bao hanh"),),
                confidence=Decimal("0.9"),
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AUTO_ASSIGNED
        assert view.suggested_department_id == PHONG_BH
        # Đã gọi router phân đúng phòng.
        assert bc.router.assigned == [(HT, PHONG_BH)]

    async def test_tin_cay_thap_giu_cho_phan(self) -> None:
        bc = _Boi()
        bc.extractor.set_result(
            ExtractionResult(
                terms=(ExtractedTerm(text="bảo hành", normalized="bao hanh"),),
                confidence=Decimal("0.3"),  # dưới ngưỡng 0.5
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS
        assert bc.router.assigned == []
        # Vẫn lưu cụm nhu cầu.
        assert len(view.extracted_terms) == 1

    async def test_mo_ho_nhieu_phong_giu_cho_phan(self) -> None:
        bc = _Boi()
        bc.extractor.set_result(
            ExtractionResult(
                terms=(
                    ExtractedTerm(text="bảo hành", normalized="bao hanh"),
                    ExtractedTerm(text="báo giá", normalized="bao gia"),
                ),
                confidence=Decimal("0.9"),
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS
        assert bc.router.assigned == []

    async def test_phan_that_bai_giu_cho_phan(self) -> None:
        bc = _Boi()
        bc.router.succeed = False
        bc.extractor.set_result(
            ExtractionResult(
                terms=(ExtractedTerm(text="lỗi bảo hành", normalized="loi bao hanh"),),
                confidence=Decimal("0.9"),
            )
        )

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.AMBIGUOUS


class TestNuotLoiLLM:
    async def test_llm_loi_khong_nem_ra_ngoai(self) -> None:
        bc = _Boi()
        bc.extractor.raise_error = True

        view = await bc.uc.execute(HT)

        # KHÔNG ném — trả NOT_ANALYZED, tin vẫn nguyên.
        assert view is not None
        assert view.outcome is AnalysisOutcome.NOT_ANALYZED
        assert view.extracted_terms == ()
        assert bc.router.assigned == []

    async def test_llm_khong_trich_duoc_gi(self) -> None:
        bc = _Boi()
        bc.extractor.set_result(ExtractionResult(terms=(), confidence=Decimal("0")))

        view = await bc.uc.execute(HT)

        assert view is not None
        assert view.outcome is AnalysisOutcome.NOT_ANALYZED


class TestBoQua:
    async def test_khong_phai_cho_phan_bo_qua(self) -> None:
        bc = _Boi(is_awaiting=False)

        view = await bc.uc.execute(HT)

        assert view is None
        # Không gọi LLM cho hội thoại đã có phòng.
        assert bc.extractor.calls == []

    async def test_khong_co_tin_bo_qua(self) -> None:
        bc = _Boi(texts=())

        view = await bc.uc.execute(HT)

        assert view is None
        assert bc.extractor.calls == []

    async def test_hoi_thoai_khong_ton_tai_bo_qua(self) -> None:
        bc = _Boi()

        view = await bc.uc.execute(new_id())

        assert view is None
