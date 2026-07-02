import pandas as pd
import tkinter as tk
from tkinter import filedialog

from TimeSlot import TimeSlot
from ClassSection import ClassSection
from Course import Course
from Schedule import Schedule
from Course import generate_all_schedules

def parse_weeks(week_str):
    weeks = set()
    if not week_str or str(week_str).strip() == '' or str(week_str).lower() == 'null': 
        return weeks
    for p in str(week_str).split(','):
        p = p.strip()
        if '-' in p:
            try:
                start, end = p.split('-')
                weeks.update(range(int(start), int(end) + 1))
            except: continue
        elif p.isdigit():
            weeks.add(int(p))
    return weeks

def get_linked_bundle(section, object_db):
    ma_hien_tai = str(section.ma_lop).replace('.0', '').strip().lower()
    ma_kem = str(section.ma_lop_kem).replace('.0', '').strip().lower()
    is_null = section.ma_lop_kem is None or ma_kem == 'null'
    ma_dai_dien =  ma_hien_tai if is_null else ma_kem
    
    
    lop_dai_dien = None
    cac_lop_kem = []
    tat_ca_cac_lop = set()
    
    for course in object_db.values():
        for s in course.classes:
            s_ma = str(s.ma_lop).replace('.0', '').strip().lower()
            s_kem = str(s.ma_lop_kem).replace('.0', '').strip().lower()
            s_is_null = s.ma_lop_kem is None or s_kem == 'null'

            # Thêm chính lớp đại diện A vào bundle
            if s_ma == ma_dai_dien and (s_is_null or s_kem == s_ma):
                lop_dai_dien = s
                tat_ca_cac_lop.add(s)
            
            # Thêm tất cả các lớp khác có mã lớp kèm là A
            if s_kem == ma_dai_dien and s_ma != ma_dai_dien:
                cac_lop_kem.append(s)
                tat_ca_cac_lop.add(s)
            
            
    valid_bundles = []
    if lop_dai_dien:
        valid_bundles.append([lop_dai_dien, cac_lop_kem])
    else:
        valid_bundles = [[section]]
        tat_ca_cac_lop.add(section)
    return valid_bundles, tat_ca_cac_lop

def load_raw_data(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, skiprows=2)
        else:
            # Ưu tiên dùng calamine để đọc Excel siêu nhanh
            try:
                df = pd.read_excel(file_path, skiprows=2, engine='calamine')
            except ImportError:
                print("Đang đọc bằng engine mặc định (chậm hơn).")
                df = pd.read_excel(file_path, skiprows=2)
            except ValueError:
                print("Đang đọc bằng engine mặc định (chậm hơn).")
                df = pd.read_excel(file_path, skiprows=2)        
        df.rename(columns=lambda x: str(x).strip(), inplace=True)
        
        needed_columns = ['Mã_lớp', 'Mã_HP', 'Tên_HP', 'Thứ', 'Thời_gian', 'Tuần', 'Cần_TN', 'Mã_lớp_kèm', 'Loại_lớp']
        existing_cols = [col for col in needed_columns if col in df.columns]
        
        df = df[existing_cols].dropna(subset=['Mã_lớp']).fillna('')
        
        df['Mã_lớp'] = df['Mã_lớp'].astype(str).str.replace('.0', '', regex=False)
        if 'Mã_lớp_kèm' in df.columns:
            df['Mã_lớp_kèm'] = df['Mã_lớp_kèm'].astype(str).str.replace('.0', '', regex=False)
            
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return []

def build_object_db(raw_data):
    course_map = {}
    for row in raw_data:
        ma_hp, ma_lop = row.get('Mã_HP'), row.get('Mã_lớp')
        if not ma_hp or not ma_lop: continue
        
        if ma_hp not in course_map: 
            course_map[ma_hp] = Course(ma_hp, row.get('Tên_HP'))
            
        course_obj = course_map[ma_hp]
        section_obj = next((s for s in course_obj.classes if s.ma_lop == ma_lop), None)
        
        if not section_obj:
            val_tn = str(row.get('Cần_TN', '')).strip().upper()
            can_tn = val_tn == "TN"
            
            section_obj = ClassSection(
                ma_lop=ma_lop,
                ma_hp=ma_hp,
                ten_hp=row.get('Tên_HP'),
                can_tn=can_tn,
                ma_lop_kem=row.get('Mã_lớp_kèm'),
                loai_lop=str(row.get('Loại_lớp', '')).strip().upper()
            )
            course_obj.add_class_section(section_obj)
            
        slot = TimeSlot(
            thu=row.get('Thứ', ''), 
            thoi_gian=row.get('Thời_gian', ''), 
            tap_hop_tuan=parse_weeks(row.get('Tuần', ''))
        )
        section_obj.add_time_slot(slot)
    return course_map
def solve_scheduling_web(object_db, selected_ma_lop_list, busy_slots):
    selected_memory = {}
    
    # Duyệt qua từng mã lớp người dùng chốt từ giao diện web (Tương tự lựa chọn số 2)
    for ma_lop in selected_ma_lop_list:
        for course_obj in object_db.values():
            target_s = next((s for s in course_obj.classes if s.ma_lop == ma_lop), None)
            if target_s:
                if target_s.loai_lop == 'TN':
                    lab_course = Course(course_obj.ma_hp + "_TN", course_obj.ten_hp + " (Thí nghiệm)")
                    selected_memory[lab_course] = [[target_s]]
                else:
                    bundles, _ = get_linked_bundle(target_s, object_db)
                    filtered_bundles = []
                    
                    for b in bundles:
                        dai_dien = b[0]
                        kems = b[1]
                        if target_s == dai_dien:
                            filtered_bundles.append(b)
                        elif target_s in kems:
                            filtered_bundles.append([dai_dien, [target_s]])
                            
                    if filtered_bundles:
                        selected_memory[course_obj] = filtered_bundles
                        
                    # Tự động kiểm tra ràng buộc Thí nghiệm
                    can_tn = False
                    for b in filtered_bundles:
                        if b[0].can_tn or any(k.can_tn for k in b[1]):
                            can_tn = True; break
                            
                    if can_tn:
                        labs = [s for s in course_obj.classes if s.loai_lop == 'TN']
                        if labs:
                            lab_course = Course(course_obj.ma_hp + "_TN", course_obj.ten_hp + " (Thí nghiệm)")
                            selected_memory[lab_course] = [[lb] for lb in labs]
                break

    flat_memory = {}
    for course, units in selected_memory.items():
        if course.ma_hp.endswith("_TN"):
            flat_memory[course] = units
        else:
            flat_units = []
            for unit in units:
                dai_dien = unit[0]
                kems = unit[1]
                if kems:
                    for k in kems:
                        flat_units.append([dai_dien, k])
                else:
                    flat_units.append([dai_dien])
            flat_memory[course] = flat_units

    # Gọi thuật toán sinh thời khóa biểu từ Course.py và trả về kết quả
    return generate_all_schedules(flat_memory, busy_slots)

def get_user_selection():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(filetypes=[("Excel/CSV Files", "*.xlsx *.xls *.csv"), ("All Files", "*.*")])
    if not file_path: return
    object_db = build_object_db(load_raw_data(file_path))
    selected_memory = {}
    busy_slots = []
    
    while True:
        print("\n" + "="*40)
        print("HỆ THỐNG XẾP LỊCH TỰ ĐỘNG")
        print("1.Thêm HỌC PHẦN ")
        print("2.Thêm MÃ LỚP")
        print("3.Xóa môn khỏi bộ nhớ")
        print("4.Xem các môn trong bộ nhớ")
        print("5.Bắt đầu Xếp lịch")
        print("6.Thêm thời gian bận")
        print("0.Exit")
        print("="*40)
        
        choice = input("Chọn: ").strip()

        if choice == '1':
            ma = input("Nhập Mã HP: ").strip().upper()
            if ma in object_db:
                course_obj = object_db[ma]
                main_units = []
                lab_units = []
                processed = set()
                
                labs = [s for s in course_obj.classes if s.loai_lop =="TN"]
                main_classes = [s for s in course_obj.classes if s not in labs]
                for mc in main_classes:
                    if mc in processed: continue
                    bundles, involved_classes = get_linked_bundle(mc, object_db)
                    processed.update(involved_classes)
                    main_units.extend(bundles) # Lưu mảng lồng: [Đại diện, [Kèm 1, Kèm 2]]
                
                if labs:
                    for lb in labs:
                        lab_units.append([lb])
                if main_units:
                    selected_memory[course_obj] = main_units
                if lab_units:
                    lab_course = Course(ma + "_TN", course_obj.ten_hp + " (Thí nghiệm)")
                    selected_memory[lab_course] = lab_units
                    
                print("-" * 60 + "\n")
            else: print("Không tìm thấy mã HP.")

        elif choice == '2':
            ma_lop = input("Nhập Mã lớp cụ thể: ").strip()
            found = False
            for course_obj in object_db.values():
                target_s = next((s for s in course_obj.classes if s.ma_lop == ma_lop), None)
                if target_s:
                    if target_s.loai_lop == 'TN':
                        print(f"Chú ý: Bạn vừa chốt một lớp Thí nghiệm.")
                        lab_course = Course(course_obj.ma_hp + "_TN", course_obj.ten_hp + " (Thí nghiệm)")
                        selected_memory[lab_course] = [[target_s]]
                    else:
                        bundles, _ = get_linked_bundle(target_s, object_db)
                        filtered_bundles = []
                        
                        # Xử lý bóc tách mảng lồng nhau
                        for b in bundles:
                            dai_dien = b[0]
                            kems = b[1]
                            # Nếu mã gõ vào là lớp Đại diện -> Lấy đại diện và TẤT CẢ lớp kèm của nó
                            if target_s == dai_dien:
                                filtered_bundles.append(b)
                            # Nếu mã gõ vào là lớp Kèm -> Lấy đại diện và CHỈ MỖI lớp kèm đó
                            elif target_s in kems:
                                filtered_bundles.append([dai_dien, [target_s]])
                                
                        if filtered_bundles:
                            selected_memory[course_obj] = filtered_bundles
                            
                        # Tự động check ràng buộc thêm lớp TN
                        can_tn = False
                        for b in filtered_bundles:
                            if b[0].can_tn or any(k.can_tn for k in b[1]):
                                can_tn = True; break
                                
                        if can_tn:
                            labs = [s for s in course_obj.classes if s.loai_lop == 'TN']
                            if labs:
                                lab_course = Course(course_obj.ma_hp + "_TN", course_obj.ten_hp + " (Thí nghiệm)")
                                selected_memory[lab_course] = [[lb] for lb in labs]
                           
                    print(f"Đã chốt mã lớp {ma_lop} cùng các nhóm liên kết .")
                    found = True; break
            if not found: print(" Không thấy mã lớp.")

        elif choice == '3':
            ma = input("Nhập Mã HP muốn xóa: ").strip().upper()
            target_main = next((c for c in selected_memory.keys() if c.ma_hp == ma), None)
            target_lab = next((c for c in selected_memory.keys() if c.ma_hp == ma + "_TN"), None)
            
            deleted = False
            if target_main: 
                del selected_memory[target_main]
                deleted = True
            if target_lab:
                del selected_memory[target_lab]
                deleted = True
                
            if deleted:
                print(f"Đã xóa {ma} (và các lớp TN liên quan nếu có) khỏi bộ nhớ.")
            else: print(" Môn này chưa có trong bộ nhớ.")
            
        elif choice == '4':
            print("\nBỘ NHỚ LỌC HIỆN TẠI:")
            if not selected_memory: print("   (Trống)")
            for course, units in selected_memory.items():
                if course.ma_hp.endswith("_TN"):
                    print(f"   - Môn {course.ma_hp}: Có {len(units)} lớp TN.")
                else:
                    print(f"   - Môn {course.ma_hp}: Có {len(units)} tổ hợp chính.")
                    # In đẹp cấu trúc mảng lồng nhau
                    for i, u in enumerate(units, 1):
                        dai_dien = u[0]
                        kems = u[1]
                        str_kems = ", ".join([k.ma_lop for k in kems]) if kems else "None"
                        print(f"      [{i}] Đại diện: {dai_dien.ma_lop:<8} | Lớp kèm: [{str_kems}]")
            if busy_slots:
                print("\nCÁC KHUNG GIỜ ĐANG BỊ CHẶN:")
                for b in busy_slots:
                    print(f"   - Thứ {b.thu} | Thời gian: {b.thoi_gian_goc}")

        elif choice == '5':
            if not selected_memory: print("Bộ nhớ trống!"); continue
            
            # --- ÉP PHẲNG (FLATTEN) CẤU TRÚC TRƯỚC KHI GỬI ĐI ---
            # Biến đổi từ: [Đại diện, [Kèm 1, Kèm 2]] -> [Đại diện, Kèm 1], [Đại diện, Kèm 2]
            flat_memory = {}
            for course, units in selected_memory.items():
                if course.ma_hp.endswith("_TN"):
                    flat_memory[course] = units
                else:
                    flat_units = []
                    for unit in units:
                        dai_dien = unit[0]
                        kems = unit[1]
                        if kems:
                            for k in kems:
                                flat_units.append([dai_dien, k])
                        else:
                            flat_units.append([dai_dien])
                    flat_memory[course] = flat_units
            
            print(f"\nĐang xử lý các thuật toán cho {len(flat_memory)} cụm môn...")
            results = generate_all_schedules(flat_memory, busy_slots)
            
            if results:
                for i, s in enumerate(results, 1):
                    print(f"\n[PHƯƠNG ÁN {i}]")
                    s.display()
                print(f"ĐÃ TÌM THẤY {len(results)} PHƯƠNG ÁN TKB")
            else:
                print("❌ Không tìm thấy phương án xếp lịch (Trùng giờ).")
                
        elif choice == '6':
            print("\n--- CÀI ĐẶT THỜI GIAN BẬN ---")
            print("1. Thêm khoảng thời gian bận")
            print("2. Xóa toàn bộ cài đặt bận")
            sub = input("Chọn (1/2): ").strip()
            
            if sub == '1':
                thu = input("Nhập Thứ muốn nghỉ (vd: 2, 3, CN): ").strip()
                buoi = input("Nhập Buổi (Sáng/Chiều/Tối) hoặc Giờ cụ thể (vd: 0600-0900): ").strip().lower()
                
                tg = ""
                if buoi in ['sáng', 'sang']: tg = "0600-1200"
                elif buoi in ['chiều', 'chieu']: tg = "1200-1800"
                elif buoi in ['tối', 'toi']: tg = "1800-2200"
                else: tg = buoi
                
                b_slot = TimeSlot(thu=thu, thoi_gian=tg, tap_hop_tuan=set(range(1, 60)))
                busy_slots.append(b_slot)
                print(f"Đã set bận lịch vào Thứ {thu}, khoảng thời gian: {tg}")
                
            elif sub == '2':
                busy_slots.clear()
                print("Đã xóa toàn bộ các khung giờ bận.")
        elif choice == '0':
            print("Tạm biệt!")
            break

if __name__ == "__main__":
    get_user_selection()

