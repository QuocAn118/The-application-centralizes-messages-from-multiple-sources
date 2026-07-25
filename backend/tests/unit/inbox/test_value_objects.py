import pytest

from src.modules.inbox.domain.value_objects.message_content import (
    AttachmentKind,
    AttachmentRef,
    EmptyMessageContentError,
    MessageContent,
)
from src.modules.inbox.domain.value_objects.platform import Platform


class TestPlatform:
    def test_co_du_ba_nen_tang_dau(self) -> None:
        assert Platform.ZALO == "ZALO"
        assert Platform.FACEBOOK == "FACEBOOK"
        assert Platform.INSTAGRAM == "INSTAGRAM"

    def test_so_sanh_truc_tiep_voi_chuoi(self) -> None:
        """StrEnum để đọc từ DB và ghi JSON không phải chuyển đổi thủ công."""
        assert Platform("ZALO") is Platform.ZALO


class TestAttachmentRef:
    def test_giu_url_va_loai(self) -> None:
        ref = AttachmentRef(
            kind=AttachmentKind.IMAGE,
            url="https://cdn.zalo.me/anh123.jpg",
            content_type="image/jpeg",
        )

        assert ref.kind is AttachmentKind.IMAGE
        assert ref.url == "https://cdn.zalo.me/anh123.jpg"

    def test_la_bat_bien(self) -> None:
        ref = AttachmentRef(kind=AttachmentKind.FILE, url="https://x/y.pdf")

        with pytest.raises(Exception):  # noqa: B017  FrozenInstanceError
            ref.url = "khac"  # type: ignore[misc]


class TestMessageContent:
    def test_chi_co_text(self) -> None:
        noi_dung = MessageContent(text="Xin chào")

        assert noi_dung.text == "Xin chào"
        assert noi_dung.attachments == ()

    def test_chi_co_attachment(self) -> None:
        ref = AttachmentRef(kind=AttachmentKind.IMAGE, url="https://x/a.jpg")
        noi_dung = MessageContent(attachments=(ref,))

        assert noi_dung.text is None
        assert len(noi_dung.attachments) == 1

    def test_ca_text_lan_attachment(self) -> None:
        ref = AttachmentRef(kind=AttachmentKind.IMAGE, url="https://x/a.jpg")
        noi_dung = MessageContent(text="Ảnh đây", attachments=(ref,))

        assert noi_dung.text == "Ảnh đây"
        assert len(noi_dung.attachments) == 1

    def test_rong_hoan_toan_bi_tu_choi(self) -> None:
        """Một tin không có text lẫn attachment là vô nghĩa — chặn ngay ở VO."""
        with pytest.raises(EmptyMessageContentError):
            MessageContent()

    def test_text_chi_co_khoang_trang_coi_nhu_rong(self) -> None:
        with pytest.raises(EmptyMessageContentError):
            MessageContent(text="   ")

    def test_co_attachment_thi_text_rong_van_hop_le(self) -> None:
        ref = AttachmentRef(kind=AttachmentKind.IMAGE, url="https://x/a.jpg")

        noi_dung = MessageContent(text="   ", attachments=(ref,))

        assert noi_dung.attachments == (ref,)
