"""Khởi tạo ``procrastinate.App`` dùng chung cho cả web server lẫn worker.

Hai tiến trình khác nhau cùng import module này: web server chỉ *đẩy* job
(``defer``), worker *chạy* job. Cùng một ``App`` nên tên task khớp nhau — worker
tra task theo tên chuỗi, lệch tên là job vào hàng đợi rồi không ai nhận.

**Kết nối DB dùng pool RIÊNG, không dùng chung pool SQLAlchemy của app.**
Procrastinate nói chuyện với psycopg thuần (nó cần ``LISTEN/NOTIFY`` và
``SELECT ... FOR UPDATE SKIP LOCKED`` do chính nó phát), trong khi app dùng
SQLAlchemy async trên cùng driver. Không có đường ghép hai bên mà không lách vào
nội bộ của cả hai. Đổi lại chỉ là một tham số cấu hình trùng (URL DB) — lấy
thẳng từ ``Settings`` nên không có nguồn cấu hình thứ hai.
"""

from procrastinate import App, PsycopgConnector

from src.shared.infrastructure.config import Settings, get_settings


def url_psycopg(settings: Settings) -> str:
    """Đổi URL SQLAlchemy sang dạng psycopg thuần.

    ``postgresql+psycopg://`` là cú pháp *dialect* của SQLAlchemy; psycopg không
    hiểu phần ``+psycopg`` và sẽ báo lỗi scheme không hợp lệ.
    """
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def tao_app(settings: Settings | None = None) -> App:
    """Dựng ``procrastinate.App`` trỏ vào cùng cơ sở dữ liệu của ứng dụng.

    ``import_paths`` để worker tự nạp module định nghĩa task: worker khởi động từ
    dòng lệnh, không đi qua ``main.py``, nên nếu không khai báo ở đây thì nó
    không biết task nào tồn tại.
    """
    cau_hinh = settings or get_settings()
    return App(
        connector=PsycopgConnector(conninfo=url_psycopg(cau_hinh)),
        import_paths=["src.jobs.tasks"],
    )


# Instance dùng chung. Tạo ở tầng module để cả server lẫn worker cùng tham chiếu
# một App; kết nối chỉ thực sự mở khi ``open_async()`` được gọi.
app = tao_app()
