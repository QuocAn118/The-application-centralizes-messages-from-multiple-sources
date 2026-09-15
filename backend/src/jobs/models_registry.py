"""Nạp toàn bộ model ORM để ``Base.metadata`` biết đủ mọi bảng.

**Vì sao cần:** SQLAlchemy chỉ giải khoá ngoại ``A.x -> B.id`` khi model của cả
A lẫn B đã được nạp. Thiếu B, lỗi ``NoReferencedTableError`` nổ ra **lúc
commit**, không phải lúc truy vấn — nên nó hiện ra rất xa chỗ gây ra.

**Ai cần:** entry point KHÔNG đi qua ``create_app()`` — hiện là worker
(``src/jobs/wiring.py``). ``migrations/env.py`` giữ danh sách riêng vì nó chạy
trước cả khi ``src.jobs`` nạp được, và Alembic cần import tường minh để
autogenerate đọc đúng metadata.

Đặt ở ``src/jobs`` (tầng composition) chứ không ở ``src/shared``: shared nằm
*dưới* mọi module nên không được biết tới chúng, dù import-linter hiện chưa cấm.

Nạp module là *tác dụng phụ* mong muốn (đăng ký bảng vào metadata), nên import ở
tầng module, không gói trong hàm. Thiếu nó, worker chết vì ``channels``
(2026-09-15).

Import ở tầng module (không trong hàm) vì đây chính là *tác dụng phụ* mong muốn:
nạp module = đăng ký bảng vào metadata.
"""

from src.modules.analytics.infrastructure.models.rollup_models import (  # noqa: F401
    AnalyticsDailyAgentModel,
    AnalyticsDailyConversationModel,
)
from src.modules.assignment.infrastructure.persistence.assignment_log_model import (  # noqa: F401
    AssignmentLogModel,
)
from src.modules.hrm.infrastructure.models.kpi_target_model import KpiTargetModel  # noqa: F401
from src.modules.hrm.infrastructure.models.request_model import RequestModel  # noqa: F401
from src.modules.hrm.infrastructure.models.shift_assignment_model import (  # noqa: F401
    ShiftAssignmentModel,
)
from src.modules.hrm.infrastructure.models.shift_model import ShiftModel  # noqa: F401
from src.modules.identity.infrastructure.models.audit_log_model import (  # noqa: F401
    AuditLogModel,
)
from src.modules.identity.infrastructure.models.department_model import (  # noqa: F401
    DepartmentModel,
)
from src.modules.identity.infrastructure.models.refresh_token_model import (  # noqa: F401
    RefreshTokenModel,
)
from src.modules.identity.infrastructure.models.user_model import UserModel  # noqa: F401
from src.modules.inbox.infrastructure.models.attachment_model import (  # noqa: F401
    AttachmentModel,
)
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel  # noqa: F401
from src.modules.inbox.infrastructure.models.conversation_model import (  # noqa: F401
    ConversationModel,
)
from src.modules.inbox.infrastructure.models.customer_model import (  # noqa: F401
    CustomerModel,
)
from src.modules.inbox.infrastructure.models.message_model import MessageModel  # noqa: F401
from src.modules.keyword.infrastructure.models.conversation_analysis_model import (  # noqa: F401
    ConversationAnalysisModel,
)
from src.modules.keyword.infrastructure.models.keyword_model import (  # noqa: F401
    KeywordModel,
)
