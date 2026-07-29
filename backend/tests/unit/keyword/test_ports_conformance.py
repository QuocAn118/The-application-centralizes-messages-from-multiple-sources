"""Xác nhận fake khớp đúng hợp đồng port/repository của keyword.

Nếu một port đổi chữ ký mà fake không theo, các phép gán dưới đây làm mypy đỏ.
"""

from src.modules.keyword.domain.ports import (
    IConversationClassifier,
    IConversationDirectory,
    IConversationRouter,
    IWorkforceDirectory,
)
from src.modules.keyword.domain.repositories.analysis_repository import (
    IAnalysisRepository,
)
from src.modules.keyword.domain.repositories.keyword_repository import (
    IKeywordRepository,
)
from tests.unit.keyword.fakes import (
    FakeAnalysisRepository,
    FakeConversationClassifier,
    FakeConversationDirectory,
    FakeConversationRouter,
    FakeKeywordRepository,
    FakeWorkforceDirectory,
)


def test_fake_khop_hop_dong_port() -> None:
    _kw_repo: IKeywordRepository = FakeKeywordRepository()
    _an_repo: IAnalysisRepository = FakeAnalysisRepository()
    _directory: IWorkforceDirectory = FakeWorkforceDirectory()
    _conv_dir: IConversationDirectory = FakeConversationDirectory()
    _router: IConversationRouter = FakeConversationRouter()
    _classifier: IConversationClassifier = FakeConversationClassifier()

    assert all(
        obj is not None for obj in (_kw_repo, _an_repo, _directory, _conv_dir, _router, _classifier)
    )
