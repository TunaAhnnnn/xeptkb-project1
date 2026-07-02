from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import uuid

from Control import build_object_db, load_raw_data, get_linked_bundle
from Course import Course, generate_all_schedules
from TimeSlot import TimeSlot

app = Flask(__name__)
# Kích hoạt CORS để cho phép ứng dụng React (thường chạy cổng 5173) gửi yêu cầu đến Flask
CORS(app)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: 
        return jsonify({'error': 'Không có file'}), 400
    file = request.files['file']
    if file.filename == '': 
        return jsonify({'error': 'Chưa chọn file'}), 400

    try:
        ext = os.path.splitext(file.filename)[1]
        temp_dir = tempfile.gettempdir()
        
        # Sử dụng chuỗi định danh ngẫu nhiên UUID để đặt tên tệp tạm,
        # tránh hiện tượng hai sinh viên upload cùng một giây bị ghi đè tệp của nhau.
        unique_filename = f"temp_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(temp_dir, unique_filename)
        file.save(temp_path)

        # Đọc cấu trúc danh sách bản ghi thô (list of dicts) từ tệp Excel/CSV
        raw_data = load_raw_data(temp_path)
        
        # Xóa ngay lập tức tệp tạm khỏi ổ cứng máy chủ sau khi đã nạp dữ liệu xong
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # Tạo cơ sở dữ liệu đối tượng tạm thời chỉ để đếm tổng số học phần hiện có
        temp_db = build_object_db(raw_data)
        
        # Trả ngược toàn bộ mảng dữ liệu thô (raw_data) về phía React.
        # Trình duyệt của từng sinh viên sẽ tự lưu giữ cục bộ mảng dữ liệu này.
        return jsonify({
            'message': 'Đã đọc file tkb thành công', 
            'total_courses': len(temp_db),
            'raw_data': raw_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search_course():
    # Chuyển sang phương thức POST để nhận tập dữ liệu raw_data từ React gửi lên
    data = request.json or {}
    raw_data = data.get('raw_data', [])
    query = data.get('q', '').strip().lower()
    
    if len(query) < 1 or not raw_data: 
        return jsonify([])
        
    # Khởi dựng bộ cơ sở dữ liệu đối tượng cục bộ bên trong phạm vi luồng xử lý của yêu cầu này
    db = build_object_db(raw_data)
    results = []
    for ma_hp, course in db.items():
        if query in ma_hp.lower() or query in course.ten_hp.lower():
            results.append({'ma_hp': ma_hp, 'ten_hp': course.ten_hp})
            if len(results) >= 5: 
                break
    return jsonify(results)

@app.route('/get_classes', methods=['POST'])
def get_classes():
    # Chuyển sang phương thức POST để nhận tập dữ liệu raw_data từ React gửi lên
    data = request.json or {}
    raw_data = data.get('raw_data', [])
    ma_hp = data.get('ma_hp', '').strip().upper()
    
    if not raw_data:
        return jsonify({'bundles': [], 'labs': []})
        
    db = build_object_db(raw_data)
    if ma_hp not in db: 
        return jsonify({'bundles': [], 'labs': []})
    
    course = db[ma_hp]
    processed = set()
    bundles_data = []

    labs = [s for s in course.classes if s.loai_lop == "TN"]
    main_classes = [s for s in course.classes if s not in labs]

    def extract_time(section):
        if not section.time_slots: 
            return "", ""
        return ", ".join([t.thu for t in section.time_slots]), ", ".join([t.thoi_gian_goc for t in section.time_slots])

    for mc in main_classes:
        if mc in processed: 
            continue
        bundles, involved = get_linked_bundle(mc, db)
        processed.update(involved)
        
        for b in bundles:
            dai_dien = b[0]
            kems = b[1] if len(b) > 1 else []
            thu_dd, tg_dd = extract_time(dai_dien)
            kem_data = []
            for k in kems:
                thu_k, tg_k = extract_time(k)
                kem_data.append({'ma_lop': k.ma_lop, 'loai_lop': k.loai_lop, 'thu': thu_k, 'thoi_gian': tg_k})

            bundles_data.append({
                'dai_dien': {'ma_lop': dai_dien.ma_lop, 'loai_lop': dai_dien.loai_lop, 'thu': thu_dd, 'thoi_gian': tg_dd},
                'kems': kem_data
            })

    lab_data = []
    for lb in labs:
        thu_lb, tg_lb = extract_time(lb)
        lab_data.append({'ma_lop': lb.ma_lop, 'loai_lop': lb.loai_lop, 'thu': thu_lb, 'thoi_gian': tg_lb})

    return jsonify({'bundles': bundles_data, 'labs': lab_data})

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json or {}
    # React sẽ gửi đồng thời mảng dữ liệu raw_data kèm theo các lựa chọn lớp học và lịch bận
    raw_data = data.get('raw_data', [])
    course_selections = data.get('course_selections', {})
    busy_data = data.get('busy_slots', []) 

    if not raw_data:
        return jsonify({'error': 'Dữ liệu thô trống hoặc chưa được gửi lên'}), 400

    # Khởi dựng hệ thống cơ sở dữ liệu cục bộ phục vụ riêng cho tiến trình tính toán này
    db = build_object_db(raw_data)

    busy_slots = []
    for b in busy_data:
        tg = "0600-1200" if b['buoi'] == 'sáng' else "1200-1800"
        b_slot = TimeSlot(thu=b['thu'], thoi_gian=tg, tap_hop_tuan=set(range(1, 60)))
        busy_slots.append(b_slot)

    flat_memory = {}
    
    for ma_hp, ticked_lops in course_selections.items():
        if ma_hp not in db: 
            continue
        course_obj = db[ma_hp]

        # Xử lý lớp Thí nghiệm
        labs = [s for s in course_obj.classes if s.loai_lop == 'TN' and s.ma_lop in ticked_lops]
        if labs:
            lab_course = Course(ma_hp + "_TN", course_obj.ten_hp + " (TN)")
            flat_memory[lab_course] = [[lb] for lb in labs]

        # Xử lý lớp Lý thuyết/Bài tập
        main_classes = [s for s in course_obj.classes if s.loai_lop != 'TN']
        flat_units = []
        processed = set()
        
        for mc in main_classes:
            if mc in processed: 
                continue
            bundles, involved = get_linked_bundle(mc, db)
            processed.update(involved)

            for b in bundles:
                dai_dien = b[0]
                kems = b[1] if len(b) > 1 else []

                if not kems:
                    if dai_dien.ma_lop in ticked_lops:
                        flat_units.append([dai_dien])
                else:
                    for k in kems:
                        if k.ma_lop in ticked_lops:
                            flat_units.append([dai_dien, k])
        
        if flat_units:
            unique_units = []
            seen = set()
            for unit in flat_units:
                sig = tuple(sorted([s.ma_lop for s in unit]))
                if sig not in seen:
                    seen.add(sig)
                    unique_units.append(unit)
            flat_memory[course_obj] = unique_units

    # Kích hoạt thuật toán sinh thời khóa biểu nền tảng
    schedules = generate_all_schedules(flat_memory, busy_slots)

    result_data = []
    for sched in schedules:
        sched_data = []
        for cls in sched.enrolled_classes:
            for slot in cls.time_slots:
                if slot.start_mins > 0: 
                    sched_data.append({
                        'ma_hp': cls.ma_hp,
                        'ten_hp': cls.ten_hp,
                        'ma_lop': cls.ma_lop,
                        'loai_lop': cls.loai_lop,
                        'thu': slot.thu,
                        'start_mins': slot.start_mins,
                        'end_mins': slot.end_mins,
                        'thoi_gian_goc': slot.thoi_gian_goc
                    })
        result_data.append(sched_data)

    return jsonify(result_data)

if __name__ == '__main__':
    # Chạy ứng dụng trên cổng 5000 mặc định
    app.run(debug=True, port=5000)