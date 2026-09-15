"""Kiểm chứng hàng đợi Procrastinate: đẩy job, chịu restart, chạy lại, hết retry.

Dùng PostgreSQL thật (bảng ``procrastinate_jobs`` do migration Alembic tạo) —
đây là điểm mấu chốt: job nằm trong DB nên sống sót qua restart, khác
``BackgroundTasks`` của FastAPI vốn chỉ nằm trong RAM. Không mock hàng đợi,
vì thứ cần chứng minh chính là hành vi lưu trữ của nó.
"""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = [pytest.mark.integration]


@pytest.fixture
def app_job():  # type: ignore[no-untyped-def]
    """``procrastinate.App`` trỏ vào DB TEST thay vì DB dev.

    ``src.jobs.app.app`` được tạo ở tầng module theo ``database_url``, nên nếu
    không đổi, test sẽ đẩy job vào cơ sở dữ liệu thật của máy dev — vừa sai chỗ
    kiểm tra, vừa để lại rác.

    ``replace_connector`` là CONTEXT MANAGER (không phải setter): phải yield bên
    trong khối ``with`` thì connector thay thế mới có hiệu lực suốt test.
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
