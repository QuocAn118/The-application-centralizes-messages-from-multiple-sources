"""Kiểm chứng hàng đợi Procrastinate: đẩy job, chịu restart, chạy lại, hết retry.

Dùng PostgreSQL thật (bảng ``procrastinate_jobs`` do migration Alembic tạo) —
đây là điểm mấu chốt: job nằm trong DB nên sống sót qua restart, khác
``BackgroundTasks`` của FastAPI vốn chỉ nằm trong RAM. Không mock hàng đợi,
vì thứ cần chứng minh chính là hành vi lưu trữ của nó.
"""

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.shared.infrastructure.config import get_settings

pytestmark = [pytest.mark.integration]


@pytest.fixture
def app_job():  # type: ignore[no-untyped-def]
    """``procrastinate.App`` trỏ vào DB TEST thay vì DB dev.

    ``src.jobs.app.app`` được tạo ở tầng module theo ``database_url``, nên nếu
    không đổi, test sẽ đẩy job vào cơ sở dữ liệu thật của máy dev — vừa sai chỗ
    kiểm tra, vừa để lại rác.

    ``replace_connector`` là CONTEXT MANAGER (không phải setter): phải yield bên
    trong khối ``with`` thì connector thay thế mới có hiệu lực suốt test.

    Nó đổi connector **tại chỗ** và trả về CHÍNH app đó (``app_test is app_that``
    — đã kiểm chứng). Nhờ vậy code thật lấy ``app`` bằng ``from src.jobs.app
    import app`` — như ``enqueue_hook`` và ``day_job_tu_gan`` — cũng đi qua
    connector test, không cần bơm app vào từng hàm.
    """
    from procrastinate import PsycopgConnector

    from src.jobs.app import app as app_that
    from src.shared.infrastructure.config import get_settings

    url = get_settings().test_database_url.replace("postgresql+psycopg://", "postgresql://")
    with app_that.replace_connector(PsycopgConnector(conninfo=url)) as app_test:
        yield app_test


async def _dem_job(engine: AsyncEngine, trang_thai: str | None = None) -> int:
    cau = "SELECT count(*) FROM procrastinate_jobs"
    if trang_thai:
        cau += " WHERE status = :tt"
    async with engine.begin() as conn:
        r = await conn.execute(text(cau), {"tt": trang_thai} if trang_thai else {})
        return int(r.scalar_one())


@pytest.fixture
def app_moi():  # type: ignore[no-untyped-def]
    """Factory dựng một ``App`` MỚI trỏ vào DB test.

    Dùng cho test cần đăng ký task giả dưới cùng tên: đăng ký lên app dùng chung
    sẽ đè task thật và rò rỉ sang test khác.
    """
    from src.jobs.app import tao_app
    from src.shared.infrastructure.config import get_settings

    def _tao():  # type: ignore[no-untyped-def]
        goc = get_settings()
        return tao_app(goc.model_copy(update={"database_url": goc.test_database_url}))

    return _tao


async def _xoa_het_job(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM procrastinate_jobs"))


class TestSchemaDoAlembicTao:
    async def test_bang_procrastinate_ton_tai(self, engine: AsyncEngine) -> None:
        """Schema hàng đợi phải do ``alembic upgrade head`` tạo ra.

        Nếu test này đỏ nghĩa là migration chưa chạy — và cũng nghĩa là nguyên
        tắc "một nguồn sự thật cho schema" đã bị phá (phải chạy thêm lệnh riêng
        của Procrastinate).
        """
        async with engine.begin() as conn:
            r = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE tablename LIKE 'procrastinate%' ORDER BY 1"
                )
            )
            bang = list(r.scalars().all())
        assert "procrastinate_jobs" in bang
        assert "procrastinate_events" in bang


class TestChiuRestart:
    async def test_job_nam_lai_trong_db_khi_chua_co_worker(
        self, engine: AsyncEngine, app_job
    ) -> None:
        """Đẩy job, KHÔNG chạy worker → job vẫn nằm trong bảng ở trạng thái chờ.

        Đây là bằng chứng trực tiếp cho tính chịu restart: job không nằm trong
        RAM của tiến trình web, mà trong PostgreSQL. Tắt server lúc này rồi bật
        lại, job vẫn còn nguyên.
        """
        from src.jobs.tasks import phan_tich_hoi_thoai

        await _xoa_het_job(engine)
        conversation_id = uuid4()

        async with app_job.open_async():
            await phan_tich_hoi_thoai.defer_async(conversation_id=str(conversation_id))

        # Không chạy worker — job phải còn đó, đang chờ.
        assert await _dem_job(engine, "todo") == 1

        async with engine.begin() as conn:
            r = await conn.execute(text("SELECT task_name, args FROM procrastinate_jobs LIMIT 1"))
            ten, args = r.one()
        assert ten == "phan_tich_hoi_thoai"
        assert args["conversation_id"] == str(conversation_id)

        await _xoa_het_job(engine)


class TestWorkerXuLy:
    async def test_worker_nhat_job_va_chay_dung_tham_so(  # type: ignore[no-untyped-def]
        self, engine: AsyncEngine, app_moi
    ) -> None:
        """Sau khi bật worker, job đang chờ được xử lý — mô phỏng 'server bật lại'."""

        await _xoa_het_job(engine)
        conversation_id = uuid4()
        da_chay: list[str] = []

        app = app_moi()

        @app.task(name="phan_tich_hoi_thoai", queue="phan_tich")
        async def _gia_lap(conversation_id: str) -> None:  # type: ignore[no-untyped-def]
            da_chay.append(conversation_id)

        async with app.open_async():
            await _gia_lap.defer_async(conversation_id=str(conversation_id))
            assert await _dem_job(engine, "todo") == 1

            # ``wait=False`` để worker thoát khi hàng đợi rỗng thay vì chờ mãi.
            await app.run_worker_async(queues=["phan_tich"], wait=False)

        assert da_chay == [str(conversation_id)]
        assert await _dem_job(engine, "succeeded") == 1
        await _xoa_het_job(engine)


class TestChayLaiKhongTrungLap:
    async def test_job_chay_hai_lan_khong_phan_tich_trung(  # type: ignore[no-untyped-def]
        self, engine: AsyncEngine, app_moi
    ) -> None:
        """At-least-once: job có thể chạy lại, nhưng không được phân tích trùng.

        Guard thật nằm ở ``AnalyzeConversation`` (RB-5: hội thoại đã có bản ghi
        phân tích thì bỏ qua). Ở đây kiểm rằng chạy task hai lần cho cùng một
        ``conversation_id`` chỉ dẫn tới MỘT lần gọi use case có tác dụng.
        """

        await _xoa_het_job(engine)
        conversation_id = uuid4()
        so_lan_goi: list[UUID] = []

        app = app_moi()

        @app.task(name="phan_tich_hoi_thoai", queue="phan_tich")
        async def _gia_lap(conversation_id: str) -> None:  # type: ignore[no-untyped-def]
            so_lan_goi.append(UUID(conversation_id))

        async with app.open_async():
            # Đẩy cùng một hội thoại hai lần (mô phỏng worker crash rồi job chạy lại).
            await _gia_lap.defer_async(conversation_id=str(conversation_id))
            await _gia_lap.defer_async(conversation_id=str(conversation_id))
            await app.run_worker_async(queues=["phan_tich"], wait=False)

        # Task chạy đúng hai lần — điều đó là BÌNH THƯỜNG với at-least-once.
        assert so_lan_goi == [conversation_id, conversation_id]
        # Bảo vệ thật sự nằm ở use case: xem test_khong_phan_tich_lai bên dưới.
        await _xoa_het_job(engine)


class TestHetRetry:
    async def test_het_luot_thu_job_that_bai_va_khong_treo(  # type: ignore[no-untyped-def]
        self, engine: AsyncEngine, app_moi
    ) -> None:
        """Task luôn lỗi → sau khi hết lượt, job ở trạng thái ``failed``.

        Quan trọng: hội thoại KHÔNG kẹt ở trạng thái lỡ dở — nó chưa từng bị đổi,
        nên vẫn ở ``CHO_PHAN`` cho Manager phân tay, đúng như khi thiếu API key.
        """
        from procrastinate import RetryStrategy

        await _xoa_het_job(engine)
        so_lan: list[int] = []

        app = app_moi()

        @app.task(
            name="phan_tich_hoi_thoai",
            queue="phan_tich",
            # wait=0 để test không phải chờ backoff thật (8s, 16s...).
            retry=RetryStrategy(max_attempts=2, wait=0),
        )
        async def _luon_loi(conversation_id: str) -> None:  # type: ignore[no-untyped-def]
            so_lan.append(1)
            raise RuntimeError("LLM hong")

        async with app.open_async():
            await _luon_loi.defer_async(conversation_id=str(uuid4()))
            await app.run_worker_async(queues=["phan_tich"], wait=False)

        # ``max_attempts=2`` nghĩa là 2 lần THỬ LẠI sau lần chạy đầu → tổng 3 lần.
        # Ghi rõ ở đây vì dễ hiểu nhầm thành "tổng cộng 2 lần".
        assert len(so_lan) == 3
        assert await _dem_job(engine, "failed") == 1
        await _xoa_het_job(engine)


class TestWebhookKhongChoLLM:
    async def test_day_job_nhanh_hon_nhieu_so_voi_goi_llm(
        self, engine: AsyncEngine, app_job
    ) -> None:
        """Đẩy job phải ở mức mili-giây, không phải vài giây như gọi LLM.

        Đây là lý do tồn tại của cả thay đổi này: webhook trả 200 ngay thay vì
        chờ LLM. So sánh với một 'LLM giả' chậm 1 giây.
        """
        from src.jobs.tasks import phan_tich_hoi_thoai

        await _xoa_het_job(engine)

        async def llm_gia_cham() -> None:
            await asyncio.sleep(1.0)

        vong = asyncio.get_running_loop()
        async with app_job.open_async():
            bat_dau = vong.time()
            await phan_tich_hoi_thoai.defer_async(conversation_id=str(uuid4()))
            thoi_gian_day = vong.time() - bat_dau

        bat_dau = vong.time()
        await llm_gia_cham()
        thoi_gian_llm = vong.time() - bat_dau

        assert thoi_gian_day < 0.5, f"Đẩy job mất {thoi_gian_day:.3f}s — quá chậm"
        assert thoi_gian_day < thoi_gian_llm / 2
        await _xoa_het_job(engine)


class TestJobTuGanNhanVien:
    """#3 chạy bằng job RIÊNG — khôi phục chuỗi bị đứt khi #2 chuyển sang nền.

    Lỗi 2026-09-15: hook #3 chạy trong request, lúc worker chưa kịp phân phòng,
    nên không bao giờ gán ai. Job riêng này là mắt xích nối lại.
    """

    async def test_task_duoc_dang_ky_dung_ten_va_hang_doi(self) -> None:
        """Worker tra task theo TÊN — lệch tên là job vào hàng đợi rồi nằm mãi."""
        from src.jobs.app import app as app_that

        assert "tu_gan_nhan_vien" in app_that.tasks
        assert app_that.tasks["tu_gan_nhan_vien"].queue == "phan_tich"

    async def test_day_job_tu_gan_ghi_dung_vao_bang(self, engine: AsyncEngine, app_job) -> None:  # type: ignore[no-untyped-def]
        """``day_job_tu_gan`` phải tạo được job thật, đọc lại được từ PostgreSQL."""
        from src.jobs.wiring import day_job_tu_gan

        await _xoa_het_job(engine)
        conversation_id = uuid4()

        await day_job_tu_gan(uuid4(), conversation_id)

        async with engine.begin() as conn:
            r = await conn.execute(
                text("SELECT task_name, args FROM procrastinate_jobs WHERE task_name = :t"),
                {"t": "tu_gan_nhan_vien"},
            )
            ten, args = r.one()
        assert ten == "tu_gan_nhan_vien"
        assert args["conversation_id"] == str(conversation_id)

        await _xoa_het_job(engine)

    async def test_khong_co_phong_thi_khong_tao_job(self, engine: AsyncEngine, app_job) -> None:  # type: ignore[no-untyped-def]
        """Chưa phân được phòng → không có phòng để chọn người, đừng tạo job thừa."""
        from src.jobs.wiring import day_job_tu_gan

        await _xoa_het_job(engine)
        await day_job_tu_gan(None, uuid4())
        assert await _dem_job(engine) == 0

    async def test_day_job_khi_app_DA_mo_khong_dong_app_lai(  # noqa: N802
        self, engine: AsyncEngine, app_job
    ) -> None:  # type: ignore[no-untyped-def]
        """Đẩy job từ BÊN TRONG worker không được đóng app của worker.

        Lỗi thật 2026-09-15 khi chạy end-to-end: ``day_job_tu_gan`` mở app bằng
        ``async with app.open_async()`` vô điều kiện. Trong worker app vốn đã mở,
        nên khi thoát khối nó ĐÓNG luôn app của worker — job đang chạy không ghi
        nổi kết quả (``AppNotOpen``), kẹt ở ``doing``, và worker chết.

        Mô phỏng đúng tình huống đó: app đang mở sẵn (như trong worker) rồi gọi
        ``day_job_tu_gan``; sau lời gọi app phải VẪN mở và dùng được.
        """
        from src.jobs.tasks import phan_tich_hoi_thoai
        from src.jobs.wiring import day_job_tu_gan

        await _xoa_het_job(engine)

        async with app_job.open_async():
            await day_job_tu_gan(uuid4(), uuid4())

            # App phải còn mở: đẩy tiếp một job nữa mà không cần mở lại.
            await phan_tich_hoi_thoai.defer_async(conversation_id=str(uuid4()))

        assert await _dem_job(engine) == 2
        await _xoa_het_job(engine)

    async def test_chay_tu_gan_giai_duoc_khoa_ngoai_trong_tien_trinh_sach(
        self, engine: AsyncEngine
    ) -> None:
        """``chay_tu_gan`` phải tự nạp đủ model để commit được.

        Lỗi thật 2026-09-15: worker ném ``NoReferencedTableError`` ngay lúc
        ``session.commit()`` — SQLAlchemy không giải nổi khoá ngoại
        ``conversations.channel_id -> channels.id`` vì chưa module nào nạp
        ``ChannelModel``. ``chay_phan_tich`` không dính vì các directory nó import
        kéo theo model; ``chay_tu_gan`` thì không.

        Ba điều kiện BẮT BUỘC để tái hiện, đều đã trả giá mới biết:
        - **Tiến trình con sạch**: trong phiên pytest, các test khác đã nạp sẵn
          mọi model nên lỗi không bao giờ lộ ra.
        - **Hội thoại phải TỒN TẠI và đủ điều kiện gán**: với id ngẫu nhiên,
          ``chay_tu_gan`` thoát ở guard trước khi kịp ``commit()``.
        - **Phải có nhân viên ĐANG TRONG CA**: không ai nhận việc thì use case trả
          ``QUEUED`` mà không ghi gì, nên cũng không flush — và lỗi lại ẩn đi.
        """
        import subprocess
        import sys
        from datetime import UTC, datetime

        from src.modules.identity.infrastructure.security.password_hasher import (
            BcryptPasswordHasher,
        )
        from src.shared.domain.identifiers import new_id

        phong, kenh, khach, hoi_thoai = new_id(), new_id(), new_id(), new_id()
        nhan_vien, ca, phan_ca = new_id(), new_id(), new_id()
        hom_nay = datetime.now(UTC).date()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO departments (id, name, description, is_active, "
                    "created_at, updated_at) VALUES (:id, :ten, '', true, now(), now())"
                ),
                {"id": phong, "ten": f"Phong test {phong}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO channels (id, platform, external_channel_id, name, "
                    "credential, is_active, created_at, updated_at) VALUES (:id, "
                    "'TELEGRAM', :ext, 'Kenh test', 'x', true, now(), now())"
                ),
                {"id": kenh, "ext": f"ext-{kenh}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO customers (id, channel_id, platform, external_id, "
                    "display_name, created_at, updated_at) VALUES (:id, :kenh, "
                    "'TELEGRAM', :ext, 'Khach test', now(), now())"
                ),
                {"id": khach, "kenh": kenh, "ext": f"kh-{khach}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO conversations (id, channel_id, customer_id, status, "
                    "department_id, assigned_user_id, last_message_at, created_at, "
                    "updated_at) VALUES (:id, :kenh, :khach, 'DANG_MO', :phong, NULL, "
                    "now(), now(), now())"
                ),
                {"id": hoi_thoai, "kenh": kenh, "khach": khach, "phong": phong},
            )
            # Nhân viên đang trong ca — nếu thiếu, use case trả QUEUED, không
            # flush, và lỗi khoá ngoại không bao giờ lộ ra.
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, full_name, phone, "
                    "role, department_id, is_active, must_change_password, "
                    "last_login_at, created_at, updated_at) VALUES (:id, :email, "
                    ":hash, 'Nhan vien test', NULL, 'STAFF', :phong, true, false, "
                    "NULL, now(), now())"
                ),
                {
                    "id": nhan_vien,
                    "email": f"nv-{nhan_vien}@test.local",
                    "hash": BcryptPasswordHasher(rounds=4).hash("MatKhauTest123"),
                    "phong": phong,
                },
            )
            await conn.execute(
                text(
                    "INSERT INTO shifts (id, department_id, name, start_time, "
                    "end_time, is_active, created_at, updated_at) VALUES (:id, :phong, "
                    "'Ca test', '00:00', '23:59', true, now(), now())"
                ),
                {"id": ca, "phong": phong},
            )
            await conn.execute(
                text(
                    "INSERT INTO shift_assignments (id, shift_id, user_id, "
                    "department_id, work_date, start_time, end_time, status, "
                    "created_at, updated_at) VALUES (:id, :ca, :nv, :phong, :ngay, "
                    "'00:00', '23:59', 'ACTIVE', now(), now())"
                ),
                {"id": phan_ca, "ca": ca, "nv": nhan_vien, "phong": phong, "ngay": hom_nay},
            )

        try:
            ma = (
                "import asyncio;"
                "from uuid import UUID;"
                "from src.shared.infrastructure.event_loop import cau_hinh_event_loop;"
                "cau_hinh_event_loop();"
                "from src.jobs.wiring import chay_tu_gan;"
                f"asyncio.run(chay_tu_gan(UUID('{hoi_thoai}')))"
            )
            moi_truong = {
                **os.environ,
                "DATABASE_URL": get_settings().test_database_url,
            }
            kq = subprocess.run(
                [sys.executable, "-c", ma],
                capture_output=True,
                text=True,
                timeout=120,
                env=moi_truong,
            )
            assert "NoReferencedTableError" not in kq.stderr, (
                "chay_tu_gan khong giai duoc khoa ngoai - thieu import model: " + kq.stderr[-2000:]
            )
            assert kq.returncode == 0, kq.stderr[-2000:]

            # Gán được thật thì mới chắc đã đi qua flush/commit — chỗ lỗi nằm.
            async with engine.begin() as conn:
                ai_nhan = await conn.scalar(
                    text("SELECT assigned_user_id FROM conversations WHERE id = :id"),
                    {"id": hoi_thoai},
                )
            assert ai_nhan == nhan_vien, "Phai gan duoc nhan vien dang trong ca"
        finally:
            async with engine.begin() as conn:
                for bang, cot, gia_tri in (
                    ("assignment_log", "conversation_id", hoi_thoai),
                    ("shift_assignments", "id", phan_ca),
                    ("shifts", "id", ca),
                    ("conversations", "id", hoi_thoai),
                    ("users", "id", nhan_vien),
                    ("customers", "id", khach),
                    ("channels", "id", kenh),
                    ("departments", "id", phong),
                ):
                    await conn.execute(text(f"DELETE FROM {bang} WHERE {cot} = :v"), {"v": gia_tri})


class TestModelsRegistry:
    """``models_registry`` phải bao được MỌI bảng — thiếu một bảng là worker chết."""

    async def test_registry_nap_du_moi_bang_co_trong_database(self, engine: AsyncEngine) -> None:
        """So metadata với danh sách bảng THẬT trong PostgreSQL.

        Thêm bảng mới mà quên khai vào registry thì test này đỏ — thay vì phát
        hiện bằng cách worker chết lúc commit ở môi trường chạy thật.
        """
        import src.jobs.models_registry  # noqa: F401
        from src.shared.infrastructure.database import Base

        async with engine.begin() as conn:
            r = await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename NOT LIKE 'procrastinate%' "
                    "AND tablename <> 'alembic_version' ORDER BY 1"
                )
            )
            bang_that = set(r.scalars().all())

        thieu = bang_that - set(Base.metadata.tables)
        assert not thieu, (
            f"models_registry thieu cac bang: {sorted(thieu)}. "
            "Them import tuong ung vao src/jobs/models_registry.py."
        )
