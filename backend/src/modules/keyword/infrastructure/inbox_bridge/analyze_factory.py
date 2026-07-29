"""Lắp ráp ``AnalyzeConversation`` từ một session + các factory cầu nối.

Gom chỗ dựng use case lõi vào một nơi (keyword.infrastructure) để cả hai lối vào
dùng chung: endpoint kích hoạt lại (keyword.presentation) và hook post-ingest
(composition root). Nhờ vậy presentation không cần biết cách ráp các adapter chạm
inbox/identity/Claude — chỉ truyền các factory đã có ở ``app.state``.
"""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.keyword.application.use_cases.analyze_conversation import (
    AnalyzeConversation,
)
from src.modules.keyword.domain.ports import (
    IConversationClassifier,
    IConversationDirectory,
    IConversationRouter,
    IWorkforceDirectory,
)
from src.modules.keyword.infrastructure.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from src.modules.keyword.infrastructure.repositories.keyword_repository import (
    SqlAlchemyKeywordRepository,
)
from src.shared.application.ports import IClock


def build_analyze_conversation(
    session: AsyncSession,
    *,
    classifier_factory: Callable[[], IConversationClassifier],
    conversation_directory_factory: Callable[[AsyncSession], IConversationDirectory],
    conversation_router_factory: Callable[[AsyncSession], IConversationRouter],
    workforce_factory: Callable[[AsyncSession], IWorkforceDirectory],
    clock: IClock,
) -> AnalyzeConversation:
    """Ráp ``AnalyzeConversation`` cho một ``session`` cụ thể."""
    return AnalyzeConversation(
        keyword_repo=SqlAlchemyKeywordRepository(session),
        analysis_repo=SqlAlchemyAnalysisRepository(session),
        conversation_directory=conversation_directory_factory(session),
        classifier=classifier_factory(),
        router=conversation_router_factory(session),
        workforce=workforce_factory(session),
        clock=clock,
    )
