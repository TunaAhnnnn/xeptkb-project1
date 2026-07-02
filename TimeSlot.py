import math

class TimeSlot:
    def __init__(self, thu, thoi_gian, tap_hop_tuan):
        # Hàm chuẩn hóa Thứ: Biến "2.0" hoặc " 2 " thành "2", "Chủ Nhật" thành "CN"
        def clean_thu(t):
            t_str = str(t).strip().replace('.0', '')
            if t_str.lower() in ['cn', 'chủ nhật', 'chu nhat', '8']:
                return 'CN'
            return t_str

        self.thu = clean_thu(thu)
        self.tuan = set(tap_hop_tuan)
        self.thoi_gian_goc = str(thoi_gian) 
        
        def parse_time_to_minutes(time_str):
            if not time_str or str(time_str).strip() == '' or str(time_str).lower() == 'nan':
                return 0, 0
            clean_str = str(time_str).replace(' ', '').replace(':', '')
            try:
                if '-' in clean_str:
                    start_str, end_str = clean_str.split('-')
                    def to_mins(t):
                        if len(t) < 3: return 0
                        h = int(t[:-2])  
                        m = int(t[-2:])  
                        return h * 60 + m
                    return to_mins(start_str), to_mins(end_str)
            except:
                pass
            return 0, 0

        self.start_mins, self.end_mins = parse_time_to_minutes(thoi_gian)

    def is_conflict_with(self, other_slot):
        # Giờ đây cả 2 Thứ đã được chuẩn hóa nên so sánh sẽ chính xác tuyệt đối
        if self.thu != other_slot.thu:
            return False

        if not (self.tuan & other_slot.tuan): 
            return False

        if self.start_mins == 0 or other_slot.start_mins == 0:
            return False

        thoi_gian_giao_nhau = max(self.start_mins, other_slot.start_mins) < min(self.end_mins, other_slot.end_mins)
        return thoi_gian_giao_nhau