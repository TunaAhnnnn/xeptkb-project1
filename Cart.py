class Cart:
    def __init__(self, timetable_db=None):
        self.selected_courses = set()
        self.db = timetable_db 

    def add_course(self, ma_hp):
        ma_hp = ma_hp.strip().upper()
        
        # 1. Kiểm tra xem môn này đã có trong giỏ chưa
        if ma_hp in self.selected_courses:
            return False, f"Môn '{ma_hp}' đã có trong giỏ hàng rồi!"
            
        # 2. Kiểm tra xem mã này có tồn tại trong dữ liệu trường không
        if self.db is not None:
            exists = any(lop.get('Mã_HP') == ma_hp for lop in self.db)
            if not exists:
                return False, f"Thất bại: Mã '{ma_hp}' không tồn tại trong CSDL!"
                
        # 3. Thêm thành công
        self.selected_courses.add(ma_hp)
        return True, f"Đã thêm '{ma_hp}' vào giỏ hàng."

    def remove_course(self, ma_hp):
        ma_hp = ma_hp.strip().upper()
        
        if ma_hp in self.selected_courses:
            self.selected_courses.remove(ma_hp)
            return True, f"Đã xóa '{ma_hp}' khỏi giỏ hàng."
        else:
            return False, f"Mã '{ma_hp}' hiện không có trong giỏ hàng."

    def get_all(self):
        return list(self.selected_courses)

    def is_empty(self):
        return len(self.selected_courses) == 0

    def clear(self):
        self.selected_courses.clear()
        
    def __len__(self):
  
        return len(self.selected_courses)