"""Use case CRUD từ khoá — Manager (phòng mình) và Admin.

Bất biến "một từ khoá (normalized) chỉ có một lần trong một phòng" chặn ở đây
(đọc-kiểm-ghi) và ở unique index DB.
"""

from uuid import UUID

from src.modules.keyword.application.actor import KeywordActor
from src.modules.keyword.application.authorization import (
    bao_dam_quan_ly_dung_phong,
    bao_dam_quan_ly_hoac_admin,
    pham_vi_phong_doc,
)
from src.modules.keyword.application.dto.keyword_dto import KeywordView
from src.modules.keyword.domain.entities.keyword import Keyword
from src.modules.keyword.domain.ports import IWorkforceDirectory
from src.modules.keyword.domain.repositories.keyword_repository import IKeywordRepository
from src.shared.application.exceptions import ConflictError, NotFoundError
from src.shared.application.ports import IClock


def _view(k: Keyword) -> KeywordView:
    return KeywordView(id=k.id, department_id=k.department_id, text=k.text, normalized=k.normalized)


def _khong_thay() -> NotFoundError:
    return NotFoundError("Không tìm thấy từ khoá.", code="KEYWORD_NOT_FOUND")


def _trung(da_co: Keyword) -> ConflictError:
    """409 kèm từ khoá đang tồn tại để giao diện chỉ đúng chip bị trùng.

    Không lộ gì ngoài phạm vi: người gọi đã qua ``bao_dam_quan_ly_dung_phong`` của
    chính phòng này, và từ khoá của phòng mình thì họ vốn xem được.
    """
    return ConflictError(
        "Từ khoá này đã tồn tại trong phòng.",
        code="KEYWORD_DUPLICATE",
        details={
            "existing_keyword": {
                "id": str(da_co.id),
                "text": da_co.text,
                "normalized": da_co.normalized,
            }
        },
    )


class CreateKeyword:
    """Tạo một từ khoá cho một phòng."""

    def __init__(
        self,
        keyword_repo: IKeywordRepository,
        directory: IWorkforceDirectory,
        clock: IClock,
    ) -> None:
        self._keyword_repo = keyword_repo
        self._directory = directory
        self._clock = clock

    async def execute(self, actor: KeywordActor, department_id: UUID, text: str) -> KeywordView:
        bao_dam_quan_ly_hoac_admin(actor)
        bao_dam_quan_ly_dung_phong(actor, department_id)

        if not await self._directory.department_exists_active(department_id):
            raise NotFoundError(
                "Không tìm thấy phòng ban đang hoạt động.", code="DEPARTMENT_NOT_FOUND"
            )

        keyword = Keyword.create(department_id=department_id, text=text, now=self._clock.now())
        da_co = await self._keyword_repo.get_by_normalized(department_id, keyword.normalized)
        if da_co is not None:
            raise _trung(da_co)

        await self._keyword_repo.add(keyword)
        return _view(keyword)


class UpdateKeyword:
    """Đổi nội dung một từ khoá."""

    def __init__(self, keyword_repo: IKeywordRepository, clock: IClock) -> None:
        self._keyword_repo = keyword_repo
        self._clock = clock

    async def execute(self, actor: KeywordActor, keyword_id: UUID, text: str) -> KeywordView:
        bao_dam_quan_ly_hoac_admin(actor)
        keyword = await self._keyword_repo.get_by_id(keyword_id)
        if keyword is None:
            raise _khong_thay()
        bao_dam_quan_ly_dung_phong(actor, keyword.department_id)

        keyword.rename(text, self._clock.now())
        trung = await self._keyword_repo.get_by_normalized(
            keyword.department_id, keyword.normalized
        )
        if trung is not None and trung.id != keyword.id:
            raise _trung(trung)

        await self._keyword_repo.update(keyword)
        return _view(keyword)


class DeleteKeyword:
    """Xoá một từ khoá."""

    def __init__(self, keyword_repo: IKeywordRepository) -> None:
        self._keyword_repo = keyword_repo

    async def execute(self, actor: KeywordActor, keyword_id: UUID) -> None:
        bao_dam_quan_ly_hoac_admin(actor)
        keyword = await self._keyword_repo.get_by_id(keyword_id)
        if keyword is None:
            raise _khong_thay()
        bao_dam_quan_ly_dung_phong(actor, keyword.department_id)

        await self._keyword_repo.delete(keyword.id)


class ListKeywords:
    """Liệt kê từ khoá theo phạm vi phòng của người gọi."""

    def __init__(self, keyword_repo: IKeywordRepository) -> None:
        self._keyword_repo = keyword_repo

    async def execute(self, actor: KeywordActor) -> list[KeywordView]:
        department_ids = pham_vi_phong_doc(actor)
        keywords = await self._keyword_repo.list_for_departments(department_ids)
        return [_view(k) for k in keywords]
