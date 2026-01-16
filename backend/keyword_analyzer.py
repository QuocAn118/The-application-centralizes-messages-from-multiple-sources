from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date as dt_date
from models import Keyword, User, KPI, UserShift, Message, MessageAssignment, Department
from decimal import Decimal

class KeywordAnalyzer:
    """Phân tích từ khóa và tự động giao việc cho nhân viên phù hợp"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_keywords(self, message_content: str) -> List[str]:
        """Trích xuất từ khóa từ nội dung tin nhắn"""
        # Chuyển về chữ thường để so sánh
        content_lower = message_content.lower()
        
        # Lấy tất cả keywords đang active từ database
        active_keywords = self.db.query(Keyword).filter(Keyword.is_active == True).all()
        
        matched_keywords = []
        for kw in active_keywords:
            if kw.keyword.lower() in content_lower:
                matched_keywords.append(kw)
        
        return matched_keywords
    
    def calculate_staff_score(
        self, 
        user: User, 
        matched_keywords: List[Keyword],
        current_date: dt_date = None
    ) -> Decimal:
        """
        Tính điểm ưu tiên cho nhân viên dựa trên:
        - Số lượng từ khóa khớp với phòng ban
        - KPI hiện tại (workload thấp hơn = điểm cao hơn)
        - Trạng thái làm việc (đang trong ca = điểm cao hơn)
        """
        if current_date is None:
            current_date = dt_date.today()
        
        score = Decimal(0)
        
        # 1. Điểm từ khóa khớp (0-50 điểm)
        keyword_score = Decimal(0)
        for kw in matched_keywords:
            if kw.department_id == user.department_id:
                keyword_score += Decimal(kw.priority * 10)
        
        # Giới hạn điểm từ khóa tối đa 50
        keyword_score = min(keyword_score, Decimal(50))
        score += keyword_score
        
        # 2. Điểm KPI (0-30 điểm) - workload thấp hơn = điểm cao hơn
        kpi = self.db.query(KPI).filter(
            KPI.user_id == user.id,
            KPI.metric_name == "Số tin nhắn xử lý",
            KPI.period_start <= current_date,
            KPI.period_end >= current_date
        ).first()
        
        if kpi:
            # Tính % hoàn thành KPI
            if kpi.target_value and kpi.target_value > 0:
                completion_rate = (kpi.current_value / kpi.target_value) * 100
                # Workload thấp hơn = điểm cao hơn
                kpi_score = Decimal(30) * (Decimal(100) - min(completion_rate, Decimal(100))) / Decimal(100)
                score += kpi_score
            else:
                score += Decimal(15)  # Điểm trung bình nếu không có target
        else:
            score += Decimal(20)  # Điểm cao nếu chưa có KPI (nhân viên mới)
        
        # 3. Điểm trạng thái làm việc (0-20 điểm)
        current_time = datetime.now().time()
        user_shift = self.db.query(UserShift).join(
            UserShift.shift
        ).filter(
            UserShift.user_id == user.id,
            UserShift.date == current_date,
            UserShift.status == "scheduled"
        ).first()
        
        if user_shift and user_shift.shift:
            # Kiểm tra xem có đang trong ca làm việc không
            if user_shift.shift.start_time <= current_time <= user_shift.shift.end_time:
                score += Decimal(20)  # Đang trong ca
            else:
                score += Decimal(5)   # Có ca nhưng chưa đến hoặc đã qua
        else:
            score += Decimal(0)  # Không có ca làm việc
        
        return score
    
    def find_best_staff(
        self, 
        message_content: str,
        current_date: dt_date = None
    ) -> Tuple[Optional[User], Decimal, List[Keyword]]:
        """
        Tìm nhân viên phù hợp nhất để xử lý tin nhắn
        
        Returns:
            Tuple[User, score, matched_keywords]
        """
        # 1. Trích xuất từ khóa
        matched_keywords = self.extract_keywords(message_content)
        
        if not matched_keywords:
            # Không có từ khóa khớp, trả về None
            return None, Decimal(0), []
        
        # 2. Lấy danh sách phòng ban liên quan
        department_ids = list(set([kw.department_id for kw in matched_keywords]))
        
        # 3. Lấy danh sách nhân viên trong các phòng ban đó
        staff_users = self.db.query(User).filter(
            User.role == "staff",
            User.is_active == True,
            User.department_id.in_(department_ids)
        ).all()
        
        if not staff_users:
            # Không có nhân viên phù hợp
            return None, Decimal(0), matched_keywords
        
        # 4. Tính điểm cho từng nhân viên
        best_staff = None
        best_score = Decimal(0)
        
        for staff in staff_users:
            score = self.calculate_staff_score(staff, matched_keywords, current_date)
            if score > best_score:
                best_score = score
                best_staff = staff
        
        return best_staff, best_score, matched_keywords
    
    def auto_assign_message(
        self, 
        message: Message,
        assigned_by_id: Optional[int] = None
    ) -> Optional[MessageAssignment]:
        """
        Tự động giao tin nhắn cho nhân viên phù hợp
        
        Args:
            message: Message object cần giao
            assigned_by_id: ID của người giao việc (None nếu là hệ thống)
        
        Returns:
            MessageAssignment object nếu thành công, None nếu không tìm được nhân viên
        """
        # Tìm nhân viên phù hợp
        best_staff, score, matched_keywords = self.find_best_staff(message.content)
        
        if not best_staff:
            return None
        
# Tạo assignment
        assignment = MessageAssignment(
            message_id=message.id,
            assigned_to=best_staff.id,
            assigned_by=assigned_by_id,
            match_score=score,
            notes=f"Tự động giao dựa trên từ khóa: {', '.join([kw.keyword for kw in matched_keywords])}"
        )
        
        self.db.add(assignment)

        # Cập nhật trạng thái tin nhắn
        message.status = "assigned"

                # Cập nhật KPI của nhân viên
        current_date = dt_date.today()
        kpi = self.db.query(KPI).filter(
            KPI.user_id == best_staff.id,
            KPI.metric_name == "Số tin nhắn xử lý",
            KPI.period_start <= current_date,
            KPI.period_end >= current_date
        ).first()
        
        if kpi:
            kpi.current_value = (kpi.current_value or Decimal(0)) + Decimal(1)
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment

       
