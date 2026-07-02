class ClassSection:
    def __init__(self, ma_lop, ma_hp, ten_hp, can_tn=False, ma_lop_kem=None, loai_lop=None):
        self.ma_lop = str(ma_lop)
        self.ma_hp = ma_hp
        self.ten_hp = ten_hp
        self.can_tn = can_tn  
        self.ma_lop_kem = str(ma_lop_kem) if ma_lop_kem else None 
        self.loai_lop = loai_lop 
        self.time_slots = [] 

    def add_time_slot(self, timeslot):
        self.time_slots.append(timeslot)

    def is_conflict_with(self, other_section):
        """Kiểm tra xung đột giữa 2 lớp (bao gồm tất cả các buổi học của chúng)"""
        for my_slot in self.time_slots:
            for their_slot in other_section.time_slots:
                if my_slot.is_conflict_with(their_slot):
                    return True
        return False