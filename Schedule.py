# File: Schedule.py
class Schedule:
    def __init__(self):
        self.enrolled_classes = [] 

    def add_class(self, class_section):
        self.enrolled_classes.append(class_section)

    def display(self):
        print("\n" + "-"*65)
        print(f"{'Mã HP':<10} | {'Mã Lớp':<10} | {'Thứ':<5} | {'Thời gian':<15} | {'Tên môn'}")
        print("-"*65)
        all_sessions = []
        for cls in self.enrolled_classes:
            for slot in cls.time_slots:
                all_sessions.append({
                    'ma_hp': cls.ma_hp, 'ma_lop': cls.ma_lop,
                    'thu': slot.thu, 'tg': slot.thoi_gian_goc, 'ten': cls.ten_hp
                })
        all_sessions.sort(key=lambda x: str(x['thu']))
        for s in all_sessions:
            print(f"{s['ma_hp']:<10} | {s['ma_lop']:<10} | {s['thu']:<5} | {s['tg']:<15} | {s['ten']}")
        print("-" * 65)