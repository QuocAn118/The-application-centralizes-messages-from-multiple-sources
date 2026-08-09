"""Endpoint inbox: liệt kê, xem, trả lời, phân, nhận, đóng hội thoại."""

import logging
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from src.modules.inbox.application.use_cases.assign_conversation_to_department import (
    AssignConversationToDepartment,
)
from src.modules.inbox.application.use_cases.close_conversation import CloseConversation
from src.modules.inbox.application.use_cases.get_conversation import GetConversation
from src.modules.inbox.application.use_cases.list_inbox import ListInbox
from src.modules.inbox.application.use_cases.reply_to_conversation import (
    ReplyToConversation,
)
from src.modules.inbox.application.use_cases.take_conversation import TakeConversation
from src.modules.inbox.domain.entities.conversation import ConversationStatus
from src.modules.inbox.domain.ports import ClosedConversation
from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    MessageContent,
)
from src.modules.inbox.infrastructure.attachments.signed_url import (
    AttachmentUrlSigner,
    SignedUrlError,
)
from src.modules.inbox.infrastructure.repositories.channel_repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.inbox.infrastructure.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
)
from src.modules.inbox.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.modules.inbox.infrastructure.repositories.message_repository import (
    SqlAlchemyMessageRepository,
)
from src.modules.inbox.presentation.dependencies import (
    Actor,
    AttachmentStore,
    Cipher,
    Clock,
    DbSession,
    Directory,
    Notifier,
    Registry,
    SettingsDep,
    UrlSigner,
)
from src.modules.inbox.presentation.schemas.common import PageResponse
from src.modules.inbox.presentation.schemas.inbox_schemas import (
    AssignRequest,
    ConversationResponse,
    InboxItemResponse,
    KyUrl,
    MessageResponse,
    ReplyRequest,
)
from src.shared.application.exceptions import (
    ApplicationError,
    NotFoundError,
    PermissionDeniedError,
)
from src.shared.infrastructure.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["inbox"])

# Số tin trả về mặc định khi xem một hội thoại. Dùng chung cho ``GET /inbox/{id}``
# và cho phản hồi của các hành động (take/close/assign) — hai nơi lệch nhau sẽ
# khiến client mất tin sau mỗi hành động mà không có dấu hiệu gì.
GIOI_HAN_TIN_MAC_DINH = 100


@router.get("/inbox", response_model=PageResponse[InboxItemResponse])
async def liet_ke_inbox(
    actor: Actor,
    session: DbSession,
    status: ConversationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: Annotated[str | None, Query(max_length=200, description="Tìm theo tên khách")] = None,
) -> PageResponse[InboxItemResponse]:
    trang = await ListInbox(
        SqlAlchemyConversationRepository(session),
        SqlAlchemyCustomerRepository(session),
        SqlAlchemyChannelRepository(session),
        SqlAlchemyMessageRepository(session),
    ).execute(actor=actor, status=status, limit=limit, offset=offset, q=q)
    return PageResponse(
        items=[InboxItemResponse.from_dto(i) for i in trang.items],
        total=trang.total,
        limit=trang.limit,
        offset=trang.offset,
    )


def _duong_dan_tep(attachment_id: UUID, conversation_id: UUID, het_han: int, chu_ky: str) -> str:
    return (
        f"/api/v1/inbox/{conversation_id}/attachments/{attachment_id}"
        f"?expires={het_han}&signature={chu_ky}"
    )


def _bo_ky_url(signer: AttachmentUrlSigner) -> KyUrl:
    """Dựng hàm sinh URL đã ký (tương đối) cho tệp đính kèm.

    Cố ý trả đường dẫn TƯƠNG ĐỐI: server không biết mình đứng sau proxy hay tên
    miền nào, đoán ở đây sẽ sai khi triển khai. Client tự ghép origin.
    """

    def ky(attachment_id: UUID, conversation_id: UUID) -> str:
        het_han, chu_ky = signer.ky(attachment_id, conversation_id)
        return _duong_dan_tep(attachment_id, conversation_id, het_han, chu_ky)

    return ky


def _bo_url_cong_khai(
    signer: AttachmentUrlSigner, settings: Settings
) -> Callable[[UUID, UUID], str] | None:
    """Dựng hàm sinh URL TUYỆT ĐỐI để Zalo/Meta tải ảnh về.

    Khác ``_bo_ky_url`` ở chỗ phải tuyệt đối: máy chủ nền tảng ở ngoài internet,
    đường dẫn tương đối vô nghĩa với họ. Địa chỉ công khai không suy ra được từ
    request (server thường sau NAT/proxy) nên phải cấu hình:
    ``ATTACHMENT_PUBLIC_BASE_URL``.

    Trả ``None`` khi chưa cấu hình — use case sẽ vẫn lưu ảnh vào lịch sử nhưng
    không gửi kèm ra nền tảng.
    """
    goc = settings.attachment_public_base_url.rstrip("/")
    if not goc:
        return None

    def url(attachment_id: UUID, conversation_id: UUID) -> str:
        het_han, chu_ky = signer.ky(attachment_id, conversation_id)
        return goc + _duong_dan_tep(attachment_id, conversation_id, het_han, chu_ky)

    return url


async def _doc_noi_dung_tra_loi(
    request: Request, settings: Settings
) -> tuple[str | None, list[tuple[bytes, str | None]]]:
    """Đọc text + tệp từ thân request, chấp nhận cả JSON lẫn multipart."""
    kieu = (request.headers.get("content-type") or "").lower()

    if not kieu.startswith("multipart/form-data"):
        du_lieu = ReplyRequest.model_validate(await request.json())
        return du_lieu.text, []

    form = await request.form()
    text = form.get("text")
    text = text if isinstance(text, str) and text.strip() else None

    tep: list[tuple[bytes, str | None]] = []
    for muc in form.getlist("files"):
        if isinstance(muc, str):
            continue
        noi_dung = await muc.read()
        if not noi_dung:
            continue
        if len(noi_dung) > settings.attachment_max_bytes:
            raise ApplicationError(
                f"Tệp vượt quá {settings.attachment_max_bytes // (1024 * 1024)}MB.",
                code="ATTACHMENT_TOO_LARGE",
            )
        loai = (muc.content_type or "").lower()
        # Chỉ nhận ảnh: #1 chưa hỗ trợ gửi tệp thường ra nền tảng, và nhận bừa
        # rồi im lặng bỏ qua sẽ khiến người dùng tưởng đã gửi được.
        if not loai.startswith("image/"):
            raise ApplicationError("Chỉ gửi được tệp ảnh.", code="ATTACHMENT_TYPE_UNSUPPORTED")
        tep.append((noi_dung, muc.content_type))

    if text is None and not tep:
        raise ApplicationError("Tin trả lời phải có nội dung.", code="EMPTY_REPLY")
    return text, tep


@router.get("/inbox/{conversation_id}", response_model=ConversationResponse)
async def xem_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    signer: UrlSigner,
    limit: Annotated[int, Query(ge=1, le=200)] = GIOI_HAN_TIN_MAC_DINH,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationResponse:
    view = await GetConversation(
        SqlAlchemyConversationRepository(session),
        SqlAlchemyMessageRepository(session),
        SqlAlchemyChannelRepository(session),
        SqlAlchemyCustomerRepository(session),
    ).execute(actor=actor, conversation_id=conversation_id, limit=limit, offset=offset)
    return ConversationResponse.from_dto(view, _bo_ky_url(signer))


@router.get("/inbox/{conversation_id}/attachments/{attachment_id}")
async def tai_tep_dinh_kem(
    conversation_id: UUID,
    attachment_id: UUID,
    session: DbSession,
    store: AttachmentStore,
    signer: UrlSigner,
    # Nhận dạng tuỳ chọn rồi tự kiểm, thay vì để FastAPI ép kiểu: tham số bắt
    # buộc/sai kiểu sẽ trả 422 và phân biệt được với 403, thành ra người ngoài
    # dò được URL nào là tệp có thật — đúng thứ chữ ký sinh ra để che.
    expires: Annotated[str | None, Query()] = None,
    signature: Annotated[str | None, Query()] = None,
) -> FileResponse:
    """Phục vụ một tệp đính kèm qua liên kết đã ký.

    **Cố ý KHÔNG dùng Bearer token**: thẻ ``<img>`` của trình duyệt không gửi
    được header ``Authorization``. Quyền được kiểm bằng chữ ký hết hạn — chữ ký
    chỉ được cấp trong phản hồi của ``GET /inbox/{id}``, mà endpoint đó đã kiểm
    quyền người gọi. Ai không xem được hội thoại thì không bao giờ nhận được
    chữ ký.
    """
    try:
        if expires is None or signature is None:
            raise SignedUrlError("Liên kết không hợp lệ.")
        signer.xac_minh(attachment_id, conversation_id, int(expires), signature)
    except (SignedUrlError, ValueError) as loi:
        # 403 cho MỌI trường hợp chữ ký hỏng — thiếu, sai định dạng, sai, hết hạn.
        # Một mã duy nhất để không tiết lộ tệp có tồn tại hay không.
        raise PermissionDeniedError(
            "Liên kết không hợp lệ hoặc đã hết hạn.", code="ATTACHMENT_LINK_INVALID"
        ) from loi

    ket_qua = await SqlAlchemyMessageRepository(session).get_attachment_with_conversation(
        attachment_id
    )
    if ket_qua is None:
        raise NotFoundError("Không tìm thấy tệp đính kèm.", code="ATTACHMENT_NOT_FOUND")

    attachment, conversation_cua_tep = ket_qua
    # Chữ ký gắn với một cặp (tệp, hội thoại); kiểm lại với dữ liệu thật để URL
    # ký cho hội thoại này không dùng để lấy tệp của hội thoại khác.
    if conversation_cua_tep != conversation_id:
        raise NotFoundError("Không tìm thấy tệp đính kèm.", code="ATTACHMENT_NOT_FOUND")

    try:
        duong_dan = store.resolve(attachment.stored_path)
    except ValueError as loi:
        raise NotFoundError("Không tìm thấy tệp đính kèm.", code="ATTACHMENT_NOT_FOUND") from loi

    if not duong_dan.is_file():
        raise NotFoundError("Không tìm thấy tệp đính kèm.", code="ATTACHMENT_NOT_FOUND")

    return FileResponse(
        duong_dan,
        media_type=attachment.content_type or "application/octet-stream",
        # inline để hiện trong thẻ <img>; nosniff để trình duyệt không tự đoán
        # kiểu nội dung (tệp do khách gửi lên, không hoàn toàn tin được).
        headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/inbox/{conversation_id}/reply", response_model=MessageResponse)
async def tra_loi(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    registry: Registry,
    cipher: Cipher,
    store: AttachmentStore,
    notifier: Notifier,
    clock: Clock,
    request: Request,
    signer: UrlSigner,
    settings: SettingsDep,
) -> MessageResponse:
    """Trả lời hội thoại bằng text và/hoặc ảnh.

    Nhận cả hai kiểu thân request:
    - ``application/json`` — ``{"text": "..."}`` như trước, không đổi;
    - ``multipart/form-data`` — trường ``text`` và các tệp ``files``.

    Giữ nhánh JSON để client cũ không hỏng khi hợp đồng mở rộng.
    """
    text, tep = await _doc_noi_dung_tra_loi(request, settings)

    use_case = ReplyToConversation(
        conversation_repo=SqlAlchemyConversationRepository(session),
        channel_repo=SqlAlchemyChannelRepository(session),
        customer_repo=SqlAlchemyCustomerRepository(session),
        message_repo=SqlAlchemyMessageRepository(session),
        adapters=registry,
        cipher=cipher,
        attachment_store=store,
        notifier=notifier,
        clock=clock,
        public_url=_bo_url_cong_khai(signer, settings),
    )
    view = await use_case.execute(
        actor=actor,
        conversation_id=conversation_id,
        content=MessageContent(
            text=text,
            attachments=tuple(
                AttachmentRef(kind=AttachmentKind.IMAGE, content_type=ct) for _, ct in tep
            ),
        ),
        raw_attachments=[du_lieu for du_lieu, _ in tep],
    )

    # Tin outbound vừa gửi (đã commit) → hook hạ nguồn (analytics #5) cộng rollup.
    # Router chỉ gọi callable app.state; không import analytics. Bọc try/except để
    # hook không làm hỏng phản hồi (nhất quán F-C).
    await session.commit()
    post_reply_hooks = getattr(request.app.state, "post_reply_hooks", ())
    for hook in post_reply_hooks:
        try:
            await hook(conversation_id, actor.user_id, view.created_at)
        except Exception:
            logger.exception(
                "Hook post-reply lỗi — bỏ qua",
                extra={"conversation_id": str(conversation_id)},
            )

    # Truyền signer dù #1 chỉ gửi text (``attachments`` luôn rỗng): khi mở nợ
    # đính kèm outbound, thiếu nó sẽ là lỗi im lặng — ảnh vừa gửi hiện thành ô xám.
    return MessageResponse.from_dto(view, _bo_ky_url(signer), conversation_id)


async def _tra_ve_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    signer: AttachmentUrlSigner,
) -> ConversationResponse:
    """Đọc lại hội thoại để trả về sau một hành động (take/close/assign).

    Hai chi tiết dễ sai, đều làm hỏng giao diện chứ không báo lỗi:
    - **Phải truyền ``signer``**, nếu không đính kèm trả về ``url: null`` và
      client ghi đè cache khiến ảnh đang hiện biến thành ô xám.
    - **Phải lấy cùng số tin như ``GET /inbox/{id}``** (``GIOI_HAN_TIN_MAC_DINH``);
      mặc định 50 của use case sẽ cắt mất tin của hội thoại dài, mà ``messages``
      là trường bắt buộc nên client không có cách nào phát hiện thiếu.
    """
    view = await GetConversation(
        SqlAlchemyConversationRepository(session),
        SqlAlchemyMessageRepository(session),
        SqlAlchemyChannelRepository(session),
        SqlAlchemyCustomerRepository(session),
    ).execute(
        actor=actor,
        conversation_id=conversation_id,
        limit=GIOI_HAN_TIN_MAC_DINH,
    )
    return ConversationResponse.from_dto(view, _bo_ky_url(signer))


@router.post("/inbox/{conversation_id}/assign", response_model=ConversationResponse)
async def phan_phong(
    conversation_id: UUID,
    du_lieu: AssignRequest,
    actor: Actor,
    session: DbSession,
    directory: Directory,
    notifier: Notifier,
    clock: Clock,
    signer: UrlSigner,
) -> ConversationResponse:
    await AssignConversationToDepartment(
        conversation_repo=SqlAlchemyConversationRepository(session),
        directory=directory,
        notifier=notifier,
        clock=clock,
    ).execute(actor=actor, conversation_id=conversation_id, department_id=du_lieu.department_id)
    return await _tra_ve_hoi_thoai(conversation_id, actor, session, signer)


@router.post("/inbox/{conversation_id}/take", response_model=ConversationResponse)
async def nhan_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    notifier: Notifier,
    clock: Clock,
    signer: UrlSigner,
) -> ConversationResponse:
    await TakeConversation(
        conversation_repo=SqlAlchemyConversationRepository(session),
        notifier=notifier,
        clock=clock,
    ).execute(actor=actor, conversation_id=conversation_id)
    return await _tra_ve_hoi_thoai(conversation_id, actor, session, signer)


@router.post("/inbox/{conversation_id}/close", response_model=ConversationResponse)
async def dong_hoi_thoai(
    conversation_id: UUID,
    actor: Actor,
    session: DbSession,
    notifier: Notifier,
    clock: Clock,
    request: Request,
    signer: UrlSigner,
) -> ConversationResponse:
    conversation = await CloseConversation(
        conversation_repo=SqlAlchemyConversationRepository(session),
        notifier=notifier,
        clock=clock,
    ).execute(actor=actor, conversation_id=conversation_id)
    phan_hoi = await _tra_ve_hoi_thoai(conversation_id, actor, session, signer)

    # Nhân viên vừa rảnh ra → các hook hạ nguồn (assignment #3 kéo hàng đợi;
    # analytics #5 cộng rollup). Composition root đăng ký callable vào app.state;
    # router chỉ gọi (không import assignment/analytics — giữ inbox ⊥ hạ nguồn).
    # Commit thao tác đóng TRƯỚC khi chạy hook: hook chạy trên session RIÊNG nên cần
    # dữ liệu đã thấy được. Payload ClosedConversation chung cho mọi hook post-close.
    await session.commit()
    closed = ClosedConversation(
        conversation_id=conversation.id,
        department_id=conversation.department_id,
        assigned_user_id=conversation.assigned_user_id,
        closed_at=clock.now(),
    )

    # Đóng đã hoàn tất (commit + notify). Lỗi hook KHÔNG được biến thành 500 cho
    # thao tác đã thành công — bọc try/except ở đây thay vì tin mọi hook tự nuốt
    # lỗi (không phụ thuộc ngầm khi thêm hook mới về sau).
    post_close_hooks = getattr(request.app.state, "post_close_hooks", ())
    for hook in post_close_hooks:
        try:
            await hook(closed)
        except Exception:
            logger.exception(
                "Hook post-close lỗi — bỏ qua, hội thoại vẫn đã đóng",
                extra={"conversation_id": str(conversation_id)},
            )

    return phan_hoi
