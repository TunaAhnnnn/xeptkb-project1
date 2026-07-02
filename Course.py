
from Schedule import Schedule

class Course:
    def __init__(self, ma_hp, ten_hp):
        self.ma_hp = ma_hp
        self.ten_hp = ten_hp
        self.classes = [] # Chứa các đối tượng ClassSection

    def add_class_section(self, class_section):
        self.classes.append(class_section)
        
    def get_all_classes(self):
        return self.classes

def generate_all_schedules(memory_map, busy_slots=None):
    if busy_slots is None: 
        busy_slots = []
    clean_memory = {}
    for course, units in memory_map.items():
        valid_units = []
        for unit in units:
            total_conflict = False
            
            # 1. Check unit có tự xung đột nội bộ không
            for i in range(len(unit)):
                for j in range(i + 1, len(unit)):
                    if unit[i].is_conflict_with(unit[j]):
                        total_conflict = True; break
                if total_conflict: break
            
            # 2. Check unit có đụng giờ bận không
            if not total_conflict and busy_slots:
                for section in unit:
                    for class_slot in section.time_slots:
                        for busy in busy_slots:
                            if class_slot.is_conflict_with(busy):
                                total_conflict = True; break
                        if total_conflict: break
                    if total_conflict: break
            
            if not total_conflict:
                valid_units.append(unit)
        
        # Nếu có 1 môn không còn tổ hợp nào hợp lệ -> Chắc chắn không xếp được TKB
        if not valid_units:
            return [] 
            
        clean_memory[course] = valid_units

    courses = sorted(list(clean_memory.keys()), key=lambda c: len(clean_memory[c]))
    
    results = []
    seen_schedules = set() 

    def backtrack(course_idx, current_schedule_obj):
        if course_idx == len(courses):
            fingerprint = tuple(sorted([c.ma_lop for c in current_schedule_obj.enrolled_classes]))
            if fingerprint not in seen_schedules:
                seen_schedules.add(fingerprint)
                final_sched = Schedule()
                final_sched.enrolled_classes = list(current_schedule_obj.enrolled_classes)
                results.append(final_sched)
            return

        current_course = courses[course_idx]
        possible_units = clean_memory[current_course]

        for unit in possible_units:
            conflict = False
            
            for section_in_unit in unit:
                for enrolled in current_schedule_obj.enrolled_classes:
                    if section_in_unit.is_conflict_with(enrolled):
                        conflict = True; break
                if conflict: break
            
            if not conflict:
                for s in unit: current_schedule_obj.add_class(s)
                backtrack(course_idx + 1, current_schedule_obj)
                for _ in range(len(unit)): current_schedule_obj.enrolled_classes.pop()

    backtrack(0, Schedule())
    return results