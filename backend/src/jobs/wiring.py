"""Lắp ráp phụ thuộc cho worker — tương đương ``main.py`` nhưng cho tiến trình job.

Worker khởi động từ dòng lệnh, KHÔNG đi qua ``create_app()``, nên nó phải tự
dựng engine, session factory, classifier và các cầu nối. Đây là lý do file này
tồn tại thay vì gọi lại wiring của web app.

Hàm ``tao_classifier`` được ``main.py`` dùng chung: chọn nhà cung cấp LLM là
quyết định phải giống hệt ở hai tiến trình — server bảo "dùng Gemini" mà worker
lại chạy Claude thì kết quả phân tích khác nhau tuỳ ai xử lý.
"""

import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.modules.keyword.domain.ports import ClassifierError, IConversationClassifier
from src.shared.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class PhanTichThatBaiError(RuntimeError):
    """LLM không phân tích được — ném ra để hàng đợi thử lại.

    Cố ý là lỗi riêng, không dùng ``ClassifierError``: use case bắt loại đó và
    nuốt, còn ở đây ta CẦN nó nổi lên tới worker.
    """


class _KhongBaoRealtime:
    """Notifier rỗng cho worker.

    ``InboxConversationRouter`` yêu cầu một ``IRealtimeNotifier`` và use case gán
    phòng sẽ GỌI nó — truyền ``None`` sẽ nổ ``AttributeError`` giữa lúc phân.
    Worker là tiến trình riêng, không giữ WebSocket nào (kết nối WS nằm ở tiến
    trình web), nên không có ai để đẩy tín hiệu tới.

    Hệ quả chấp nhận được: client không nhận tín hiệu tức thì khi hội thoại được
    tự phân, mà thấy ở lần gọi REST kế tiếp (chuyển trang/refetch). Phân tích vốn
    là việc nền, không phải tương tác tức thời.
    """

    async def notify_conversation_changed(
        self, conversation_id: UUID, department_id: UUID | None, change: str
    ) -> None:
        return None


class _KhongCauHinhLLM:
    """Classifier luôn lỗi — dùng khi chưa cấu hình nhà cung cấp nào.

    Ném ``ClassifierError`` thay vì im lặng: use case ghi nhận "không phân tích
    được" và giữ hội thoại ở CHO_PHAN cho Manager phân tay.
    """

    def __init__(self, ly_do: str) -> None:
        self._ly_do = ly_do

    async def classify(self, texts, departments):  # type: ignore[no-untyped-def]
        raise ClassifierError(self._ly_do)


def tao_classifier(settings: Settings) -> Callable[[], IConversationClassifier]:
    """Chọn adapter LLM theo ``LLM_PROVIDER``; trả factory dựng classifier.

    Dùng chung cho web app lẫn worker để hai bên không bao giờ chạy khác nhà
    cung cấp.
    """
    nha_cung_cap = settings.llm_provider.strip().lower()

    if nha_cung_cap == "gemini" and settings.gemini_api_key:
        from src.modules.keyword.infrastructure.classifier.gemini_classifier import (
            GeminiConversationClassifier,
        )

        khoa, model = settings.gemini_api_key, settings.gemini_model
        logger.info("Phân tích #2 dùng Gemini (model %s).", model)
        return lambda: GeminiConversationClassifier(khoa, model)

    if nha_cung_cap == "claude" and settings.anthropic_api_key:
        from anthropic import AsyncAnthropic

        from src.modules.keyword.infrastructure.classifier.claude_classifier import (
            ClaudeConversationClassifier,
        )

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        model = settings.anthropic_model
        logger.info("Phân tích #2 dùng Claude (model %s).", model)
        return lambda: ClaudeConversationClassifier(client, model)

    if nha_cung_cap in ("gemini", "claude"):
        thieu = "GEMINI_API_KEY" if nha_cung_cap == "gemini" else "ANTHROPIC_API_KEY"
        ly_do = f"LLM_PROVIDER={nha_cung_cap} nhưng thiếu {thieu}."
    else:
        ly_do = f"LLM_PROVIDER={nha_cung_cap or '(rỗng)'} — phân tích tắt."
    logger.warning("%s Phân tích #2 vô hiệu: hội thoại ở lại CHO_PHAN để phân tay.", ly_do)
    return lambda: _KhongCauHinhLLM(ly_do)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _lay_session_factory() -> async_sessionmaker[AsyncSession]:
    """Dựng engine một lần cho cả vòng đời worker.

    Không dựng lại mỗi job: mỗi engine kéo theo một pool kết nối riêng, tạo mới
    liên tục sẽ làm cạn kết nối PostgreSQL sau vài trăm job.

    Nạp ``models_registry`` ở đây — điểm mọi job đều đi qua — để SQLAlchemy giải
    được khoá ngoại lúc commit. Xem module đó để biết vì sao cần.
    """
    global _engine, _session_factory
    if _session_factory is None:
        from src.jobs import models_registry  # noqa: F401
        from src.shared.infrastructure.database import create_engine_and_session_factory

        _engine, _session_factory = create_engine_and_session_factory(get_settings().database_url)
    return _session_factory


async def chay_phan_tich(conversation_id: UUID) -> None:
    """Chạy ``AnalyzeConversation`` cho một hội thoại, trong session riêng.

    Giữ đúng hành vi của hook cũ (phiên riêng, commit cuối), chỉ khác chỗ chạy:
    tiến trình worker thay vì request webhook. Lỗi được để ném ra ngoài cho
    Procrastinate retry — khác hook cũ vốn nuốt hết vì lúc đó lỗi sẽ làm hỏng
    phản hồi webhook.
    """
    from src.modules.hrm.infrastructure.directory.workforce_directory import (  # noqa: F401
        IdentityWorkforceDirectory as _HrmDirectory,
    )
    from src.modules.keyword.domain.value_objects.extracted_term import AnalysisOutcome
    from src.modules.keyword.infrastructure.directory.workforce_directory import (
        IdentityWorkforceDirectory,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.analyze_factory import (
        build_analyze_conversation,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.conversation_directory import (
        InboxConversationDirectory,
    )
    from src.modules.keyword.infrastructure.inbox_bridge.conversation_router import (
        InboxConversationRouter,
    )
    from src.shared.infrastructure.clock import SystemClock

    settings = get_settings()
    clock = SystemClock()
    session_factory = _lay_session_factory()

    logger.info("Bắt đầu phân tích hội thoại %s", conversation_id)

    async with session_factory() as session:
        use_case = build_analyze_conversation(
            session,
            classifier_factory=tao_classifier(settings),
            conversation_directory_factory=InboxConversationDirectory,
            conversation_router_factory=lambda s: InboxConversationRouter(
                s, notifier=_KhongBaoRealtime(), clock=clock
            ),
            workforce_factory=IdentityWorkforceDirectory,
            clock=clock,
        )
        ket_qua = await use_case.execute(conversation_id)
        await session.commit()

    if ket_qua is None:
        # Bỏ qua hợp lệ: hội thoại không còn CHO_PHAN, chưa có tin, hoặc đã phân
        # tích thật rồi. Không phải lỗi.
        logger.info("Bỏ qua hội thoại %s (không đủ điều kiện phân tích).", conversation_id)
        return

    logger.info(
        "Phân tích xong hội thoại %s: outcome=%s phòng=%s tin_cậy=%s cụm=%d",
        conversation_id,
        ket_qua.outcome,
        ket_qua.suggested_department_id,
        ket_qua.confidence,
        len(ket_qua.extracted_terms),
    )

    # Phân được phòng thì đẩy tiếp job gán người (#3).
    #
    # TẠI SAO Ở ĐÂY: chuỗi hook ``post_ingest`` chạy #2 rồi #3 theo thứ tự đăng
    # ký, dựa trên giả định #2 phân phòng XONG ngay trong request. Khi #2 chuyển
    # sang hàng đợi, giả định đó vỡ: hook #3 chạy lúc phòng còn NULL nên không
    # bao giờ gán ai, và không có lỗi nào hiện ra. Nối lại chuỗi tại đây — chỗ
    # duy nhất biết chắc phòng vừa được phân.
    if ket_qua.outcome is AnalysisOutcome.AUTO_ASSIGNED:
        await day_job_tu_gan(ket_qua.suggested_department_id, conversation_id)

    if ket_qua.outcome is AnalysisOutcome.NOT_ANALYZED and not ket_qua.extracted_terms:
        # LLM thất bại (mạng/quota/sai model). Use case đã nuốt lỗi và ghi
        # NOT_ANALYZED để giữ đúng hợp đồng "phân tích lỗi không làm hỏng nhận
        # tin". Nhưng ở hàng đợi thì im lặng là sai: job báo Success, retry không
        # bao giờ chạy, và không ai biết LLM đang hỏng.
        #
        # Ném lỗi ở đây để Procrastinate retry. Bản ghi NOT_ANALYZED đã commit
        # KHÔNG chặn lần thử lại — guard RB-5 cố ý bỏ qua loại bản ghi này.
        raise PhanTichThatBaiError(
            f"LLM không phân tích được hội thoại {conversation_id} — xem log phía trên."
        )


async def day_job_tu_gan(
    department_id: UUID | None,
    conversation_id: UUID | None = None,
    *,
    _day: Callable[[UUID], Awaitable[None]] | None = None,
) -> None:
    """Đẩy job ``tu_gan_nhan_vien`` khi hội thoại vừa được phân về một phòng.

    Không có phòng thì không đẩy: #3 cần biết chọn người trong phòng nào, và hội
    thoại chưa phân phòng vẫn đang chờ Manager phân tay.

    ``_day`` chỉ để test bơm hàm đẩy giả — mặc định dùng hàng đợi thật.

    Nuốt mọi lỗi: hàng đợi hỏng không được làm job phân tích (đã thành công) bị
    tính là thất bại rồi retry, vì retry sẽ gọi lại LLM một cách vô ích. Mất job
    gán chỉ nghĩa là hội thoại nằm trong hàng đợi phòng — Manager vẫn kéo tay
    được bằng ``POST /departments/{id}/auto-assign``.
    """
    if department_id is None or conversation_id is None:
        return

    try:
        if _day is not None:
            await _day(conversation_id)
            return

        from procrastinate.exceptions import AppNotOpen

        from src.jobs.app import app
        from src.jobs.tasks import tu_gan_nhan_vien

        # Hàm này chạy ở HAI nơi có trạng thái app khác nhau:
        # - trong worker: app ĐANG mở (worker tự mở để nhận job);
        # - ngoài worker (test, script): app chưa mở.
        #
        # ``async with app.open_async()`` vô điều kiện sẽ ĐÓNG app của worker khi
        # thoát khối, làm chính job đang chạy không ghi nổi kết quả —
        # ``AppNotOpen``, job kẹt ở ``doing`` và worker chết. Đã gặp thật khi chạy
        # end-to-end 2026-09-15.
        #
        # Thử đẩy trước rồi mới mở: ``AppNotOpen`` là cách duy nhất biết chắc app
        # chưa mở mà không phải đoán kiểu connector cụ thể.
        try:
            await tu_gan_nhan_vien.defer_async(conversation_id=str(conversation_id))
        except AppNotOpen:
            async with app.open_async():
                await tu_gan_nhan_vien.defer_async(conversation_id=str(conversation_id))
    except Exception:
        logger.exception(
            "Không đẩy được job tự gán cho hội thoại %s — hội thoại nằm trong hàng đợi phòng",
            conversation_id,
        )


async def chay_tu_gan(conversation_id: UUID) -> None:
    """Chạy #3 cho một hội thoại đã có phòng, trong session riêng.

    Dùng lại đúng hook post-ingest của #3 sẽ phải dựng ``InboundEvent`` giả, nên
    thay vào đó gọi thẳng use case với cùng bộ điều kiện mà hook kiểm: chỉ gán
    khi hội thoại ``DANG_MO``, có phòng, và chưa ai nhận.

    Không ai trong ca → use case trả ``QUEUED`` và hội thoại nằm lại hàng đợi
    phòng. Đó KHÔNG phải lỗi, nên không ném ra: retry cũng sẽ cho kết quả y hệt
    chừng nào chưa ai vào ca. Hook ``post_close`` và endpoint kéo tay là đường
    lấy việc ra khỏi hàng đợi.
    """
    from src.modules.assignment.infrastructure.inbox_bridge.pull_queue_factory import (
        build_auto_assign_conversation,
    )
    from src.modules.inbox.domain.entities.conversation import ConversationStatus
    from src.modules.inbox.infrastructure.repositories.conversation_repository import (
        SqlAlchemyConversationRepository,
    )
    from src.shared.infrastructure.clock import SystemClock

    settings = get_settings()
    clock = SystemClock()
    session_factory = _lay_session_factory()

    async with session_factory() as session:
        hoi_thoai = await SqlAlchemyConversationRepository(session).get_by_id(conversation_id)
        if (
            hoi_thoai is None
            or hoi_thoai.status is not ConversationStatus.DANG_MO
            or hoi_thoai.department_id is None
            or hoi_thoai.assigned_user_id is not None
        ):
            # Idempotent: job chạy lại sau khi đã gán xong thì rơi vào đây.
            logger.info("Bỏ qua tự gán hội thoại %s (không đủ điều kiện).", conversation_id)
            return

        use_case = build_auto_assign_conversation(
            session,
            notifier=_KhongBaoRealtime(),
            clock=clock,
            timezone=settings.app_timezone,
        )
        ket_cuc = await use_case.execute(conversation_id, hoi_thoai.department_id)
        await session.commit()

    logger.info("Tự gán hội thoại %s: %s", conversation_id, ket_cuc)
