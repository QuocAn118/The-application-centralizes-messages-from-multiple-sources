"""Lắp ráp phụ thuộc cho worker — tương đương ``main.py`` nhưng cho tiến trình job.

Worker khởi động từ dòng lệnh, KHÔNG đi qua ``create_app()``, nên nó phải tự
dựng engine, session factory, classifier và các cầu nối. Đây là lý do file này
tồn tại thay vì gọi lại wiring của web app.

Hàm ``tao_classifier`` được ``main.py`` dùng chung: chọn nhà cung cấp LLM là
quyết định phải giống hệt ở hai tiến trình — server bảo "dùng Gemini" mà worker
lại chạy Claude thì kết quả phân tích khác nhau tuỳ ai xử lý.
"""

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.modules.keyword.domain.ports import ClassifierError, IConversationClassifier
from src.shared.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


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
    """
    global _engine, _session_factory
    if _session_factory is None:
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
        await use_case.execute(conversation_id)
        await session.commit()
