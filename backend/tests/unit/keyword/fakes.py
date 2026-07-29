"""Fake in-memory cho unit test use case của keyword.

Fake phản ánh hành vi thật của repository/port; khi hợp đồng đổi, fake sai làm
test đỏ. Mock thì không.
"""

from datetime import datetime
from uuid import UUID

from src.modules.keyword.domain.entities.conversation_analysis import (
    ConversationAnalysis,
)
from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.ports import (
    ClassifierError,
    ConversationSnapshot,
)
from src.modules.keyword.domain.value_objects.extracted_term import (
    ClassificationResult,
    DepartmentKeywords,
)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        self._now = now


class FakeKeywordRepository:
    def __init__(self, keywords: list[Keyword] | None = None) -> None:
        self._items: dict[UUID, Keyword] = {k.id: k for k in (keywords or [])}

    async def get_by_id(self, keyword_id: UUID) -> Keyword | None:
        return self._items.get(keyword_id)

    async def get_by_normalized(self, department_id: UUID, normalized: str) -> Keyword | None:
        for k in self._items.values():
            if k.department_id == department_id and k.normalized == normalized:
                return k
        return None

    async def add(self, keyword: Keyword) -> None:
        self._items[keyword.id] = keyword

    async def update(self, keyword: Keyword) -> None:
        self._items[keyword.id] = keyword

    async def delete(self, keyword_id: UUID) -> None:
        self._items.pop(keyword_id, None)

    async def list_for_departments(self, department_ids: list[UUID] | None) -> list[Keyword]:
        items = list(self._items.values())
        if department_ids is not None:
            items = [k for k in items if k.department_id in department_ids]
        return sorted(items, key=lambda k: k.created_at)

    async def list_all_active(self) -> list[Keyword]:
        return sorted(self._items.values(), key=lambda k: k.created_at)


class FakeAnalysisRepository:
    def __init__(self) -> None:
        self.items: list[ConversationAnalysis] = []

    async def get_by_id(self, analysis_id: UUID) -> ConversationAnalysis | None:
        return next((a for a in self.items if a.id == analysis_id), None)

    async def add(self, analysis: ConversationAnalysis) -> None:
        self.items.append(analysis)

    async def list_for_conversation(self, conversation_id: UUID) -> list[ConversationAnalysis]:
        ds = [a for a in self.items if a.conversation_id == conversation_id]
        return sorted(ds, key=lambda a: a.created_at, reverse=True)

    def _loc(self, department_ids: list[UUID] | None) -> list[ConversationAnalysis]:
        ds = list(self.items)
        if department_ids is not None:
            ds = [a for a in ds if a.suggested_department_id in department_ids]
        return sorted(ds, key=lambda a: a.created_at, reverse=True)

    async def list_for_departments(
        self, department_ids: list[UUID] | None, limit: int = 50, offset: int = 0
    ) -> list[ConversationAnalysis]:
        return self._loc(department_ids)[offset : offset + limit]

    async def count_for_departments(self, department_ids: list[UUID] | None) -> int:
        return len(self._loc(department_ids))


class FakeWorkforceDirectory:
    def __init__(self) -> None:
        self.active_departments: set[UUID] = set()

    async def department_exists_active(self, department_id: UUID) -> bool:
        return department_id in self.active_departments


class FakeConversationDirectory:
    def __init__(self) -> None:
        self._snapshots: dict[UUID, ConversationSnapshot] = {}

    def set_snapshot(self, snapshot: ConversationSnapshot) -> None:
        self._snapshots[snapshot.conversation_id] = snapshot

    async def get_snapshot(
        self, conversation_id: UUID, max_messages: int
    ) -> ConversationSnapshot | None:
        snap = self._snapshots.get(conversation_id)
        if snap is None:
            return None
        # Tôn trọng max_messages như implementation thật.
        return ConversationSnapshot(
            conversation_id=snap.conversation_id,
            is_awaiting=snap.is_awaiting,
            first_texts=snap.first_texts[:max_messages],
        )


class FakeConversationRouter:
    def __init__(self) -> None:
        self.assigned: list[tuple[UUID, UUID]] = []
        self.succeed = True

    async def assign_to_department(self, conversation_id: UUID, department_id: UUID) -> bool:
        if self.succeed:
            self.assigned.append((conversation_id, department_id))
        return self.succeed


class FakeConversationClassifier:
    """Classifier giả tất định: test bơm sẵn kết quả hoặc bật lỗi.

    Ghi lại danh mục phòng được truyền vào để test khẳng định danh mục đúng
    được bơm cho LLM.
    """

    def __init__(self, result: ClassificationResult | None = None) -> None:
        self._result = result or ClassificationResult()
        self.raise_error = False
        self.calls: list[tuple[str, ...]] = []
        self.departments_seen: list[tuple[DepartmentKeywords, ...]] = []

    def set_result(self, result: ClassificationResult) -> None:
        self._result = result

    async def classify(
        self, texts: tuple[str, ...], departments: tuple[DepartmentKeywords, ...]
    ) -> ClassificationResult:
        self.calls.append(texts)
        self.departments_seen.append(departments)
        if self.raise_error:
            raise ClassifierError("LLM lỗi giả lập")
        return self._result
