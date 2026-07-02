import React, { useState, useEffect } from 'react';

const API_BASE = 'https://xeptkb-project1.onrender.com';
const START_MINS = 6 * 60 + 45;
const END_MINS = 17 * 60 + 45;
const TOTAL_MINS = END_MINS - START_MINS;
const DAYS = ['2', '3', '4', '5', '6', '7', 'CN'];

export default function App() {
  // === QUẢN LÝ TRẠNG THÁI (STATE) ===
  const [view, setView] = useState('main'); // 'main' hoặc 'schedule'
  const [rawData, setRawData] = useState(null); // Lưu dữ liệu Excel thô
  const [uploadStatus, setUploadStatus] = useState("Chưa nhận/đọc xong file");
  const [isUploaded, setIsUploaded] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  
  // Lưu môn đã chọn: { 'MI1111': { ten_hp: '...', classes: ['123', '124'] } }
  const [selectedCourses, setSelectedCourses] = useState({});
  const [busySlots, setBusySlots] = useState([]);

  // Dữ liệu Modal chọn lớp
  const [modalData, setModalData] = useState(null); 
  const [tempTickedClasses, setTempTickedClasses] = useState(new Set());

  // Dữ liệu TKB
  const [schedules, setSchedules] = useState([]);
  const [currentSchedIdx, setCurrentSchedIdx] = useState(0);

  // === CÁC HÀM XỬ LÝ (LOGIC) ===

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    setUploadStatus("Đang đọc file...");
    try {
      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        setRawData(data.raw_data);
        setUploadStatus(`${data.message} (${data.total_courses} môn)`);
        setIsUploaded(true);
      } else {
        alert(data.error);
        setUploadStatus("Lỗi khi đọc file");
      }
    } catch (err) {
      console.error(err);
      setUploadStatus("Không thể kết nối đến Server");
    }
  };

  const handleSearchChange = async (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    if (query.length < 1 || !rawData) {
      setSuggestions([]);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: query, raw_data: rawData })
      });
      const data = await res.json();
      setSuggestions(data);
    } catch (err) { console.error(err); }
  };

  const openClassModal = async (ma_hp, ten_hp) => {
    setSearchQuery("");
    setSuggestions([]);

    try {
      const res = await fetch(`${API_BASE}/get_classes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ma_hp, raw_data: rawData })
      });
      const data = await res.json();

      let initialTicked = new Set();
      if (selectedCourses[ma_hp]) {
        initialTicked = new Set(selectedCourses[ma_hp].classes);
      } else {
        // Mặc định tick tất cả nếu chưa chọn
        data.bundles.forEach(b => {
          initialTicked.add(b.dai_dien.ma_lop);
          b.kems.forEach(k => initialTicked.add(k.ma_lop));
        });
        data.labs.forEach(lb => initialTicked.add(lb.ma_lop));
      }

      setTempTickedClasses(initialTicked);
      setModalData({ ma_hp, ten_hp, bundles: data.bundles, labs: data.labs });
    } catch (err) { console.error(err); }
  };

  const toggleClassTick = (ma_lop) => {
    setTempTickedClasses(prev => {
      const newSet = new Set(prev);
      if (newSet.has(ma_lop)) newSet.delete(ma_lop);
      else newSet.add(ma_lop);
      return newSet;
    });
  };

  const confirmClassSelection = () => {
    if (tempTickedClasses.size > 0) {
      setSelectedCourses(prev => ({
        ...prev,
        [modalData.ma_hp]: { ten_hp: modalData.ten_hp, classes: Array.from(tempTickedClasses) }
      }));
    } else {
      setSelectedCourses(prev => {
        const copy = { ...prev };
        delete copy[modalData.ma_hp];
        return copy;
      });
    }
    setModalData(null);
  };

  const removeCourse = (ma_hp) => {
    setSelectedCourses(prev => {
      const copy = { ...prev };
      delete copy[ma_hp];
      return copy;
    });
  };

  const handleBusyToggle = (thu, buoi) => {
    setBusySlots(prev => {
      const exists = prev.find(b => b.thu === thu && b.buoi === buoi);
      if (exists) return prev.filter(b => !(b.thu === thu && b.buoi === buoi));
      return [...prev, { thu, buoi }];
    });
  };

  const generateSchedules = async () => {
    const payloadSelections = {};
    Object.keys(selectedCourses).forEach(ma_hp => {
      payloadSelections[ma_hp] = selectedCourses[ma_hp].classes;
    });

    if (Object.keys(payloadSelections).length === 0) {
      alert("Vui lòng chọn ít nhất 1 môn.");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          raw_data: rawData, 
          course_selections: payloadSelections, 
          busy_slots: busySlots 
        })
      });
      const data = await res.json();
      
      if (data.error) { alert(data.error); return; }
      if (data.length === 0) { alert("Không tìm thấy phương án (bị trùng lịch)."); return; }
      
      setSchedules(data);
      setCurrentSchedIdx(0);
      setView('schedule');
    } catch (err) { console.error(err); }
  };

  // === RENDER GIAO DIỆN ===

  if (view === 'schedule') {
    const currentSchedule = schedules[currentSchedIdx] || [];
    const lunchTop = ((12 * 60 - START_MINS) / TOTAL_MINS) * 100;
    const lunchHeight = (30 / TOTAL_MINS) * 100;

    return (
      <div className="w-full max-w-6xl mx-auto p-4">
        <div className="flex justify-between items-center mb-4 mt-4">
          <button onClick={() => setView('main')} className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded font-bold">
            ← Quay lại
          </button>
          <h2 className="text-2xl font-bold text-gray-800">Kết quả Xếp Lịch</h2>
          <div className="flex items-center space-x-4">
            <span className="font-medium">Phương án {currentSchedIdx + 1} / {schedules.length}</span>
            <button onClick={() => setCurrentSchedIdx(p => Math.max(0, p - 1))} className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded font-bold">&lt;</button>
            <button onClick={() => setCurrentSchedIdx(p => Math.min(schedules.length - 1, p + 1))} className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded font-bold">&gt;</button>
          </div>
        </div>

        <div className="shadow rounded relative bg-white border border-gray-300 overflow-x-auto">
          <div className="border-b border-gray-400" style={{ display: 'grid', gridTemplateColumns: '60px repeat(7, 1fr)', width: '100%', minWidth: '900px' }}>
            <div className="bg-[#2e7d32]"></div>
            {DAYS.map(d => <div key={d} className="day-header">{d === 'CN' ? 'Chủ Nhật' : `Thứ ${d}`}</div>)}
          </div>

          <div className="calendar-container">
            {/* Lưới ngang (Giờ) */}
            {[...Array(11)].map((_, i) => {
              const h = i + 7;
              const topPercent = (((h * 60) - START_MINS) / TOTAL_MINS) * 100;
              return (
                <React.Fragment key={h}>
                  <div className="time-label absolute w-[60px]" style={{ top: `${topPercent}%`, left: 0 }}>{h}:00</div>
                  <div className="absolute w-full border-t border-gray-300 pointer-events-none" style={{ top: `${topPercent}%`, left: '60px', width: 'calc(100% - 60px)' }}></div>
                </React.Fragment>
              );
            })}

            {/* Lưới dọc (Thứ) */}
            {[1, 2, 3, 4, 5, 6, 7].map(i => (
              <div key={`col-${i}`} className="absolute h-full border-l border-gray-400 pointer-events-none" style={{ top: 0, left: `calc(60px + ((100% - 60px) / 7) * ${i - 1})` }}></div>
            ))}

            {/* Khung nghỉ trưa */}
            {[1, 2, 3, 4, 5, 6, 7].map(i => (
              <div key={`lunch-${i}`} className="lunch-break" style={{ top: `${lunchTop}%`, height: `${lunchHeight}%`, left: `calc(60px + ((100% - 60px) / 7) * ${i - 1})`, width: 'calc((100% - 60px) / 7)' }}>Nghỉ trưa</div>
            ))}

            {/* Render các block môn học */}
            {currentSchedule.map((slot, idx) => {
              if (slot.start_mins < START_MINS || slot.end_mins > END_MINS) return null;
              const mapDay = { '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6, 'CN': 7 };
              const col = mapDay[slot.thu.toUpperCase()] || 1;
              const topP = ((slot.start_mins - START_MINS) / TOTAL_MINS) * 100;
              const heightP = ((slot.end_mins - slot.start_mins) / TOTAL_MINS) * 100;
              const isLab = slot.ma_hp.endsWith('_TN');

              return (
                <div key={idx} className="course-block flex flex-col justify-start z-10 hover:brightness-110" 
                     style={{
                       top: `${topP}%`, height: `${heightP}%`, 
                       left: `calc(60px + ((100% - 60px) / 7) * ${col - 1})`, 
                       width: `calc((100% - 60px) / 7)`,
                       backgroundColor: isLab ? '#b91c1c' : '#009900',
                       borderLeftColor: isLab ? '#7f1d1d' : '#1b5e20',
                       borderRightColor: isLab ? '#7f1d1d' : '#1b5e20'
                     }}>
                  <div className="text-[13px] text-green-200 font-semibold mb-1 leading-none">{slot.thoi_gian_goc}</div>
                  <div className="text-[15px] font-bold leading-tight mb-1 text-white">{slot.ma_hp} • {slot.ma_lop}</div>
                  <div className="text-[13px] font-medium leading-tight text-gray-100 opacity-90">{slot.ten_hp} • Loại: {slot.loai_lop}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // GIAO DIỆN CHÍNH (UPLOAD, TÌM KIẾM, CHỌN LỊCH BẬN)
  return (
    <div className="bg-gray-100 font-sans min-h-screen py-10">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        <h1 className="text-4xl font-bold text-center text-red-800">Xếp thời khóa biểu HUST made by Tuna</h1>

        {/* Upload Zone */}
        <div className={`p-6 rounded-lg shadow text-center transition-colors duration-300 border-2 ${isUploaded ? 'bg-green-100 border-green-500' : 'bg-red-100 border-red-500'}`}>
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Tải file excel của ae lên</h2>
          <input type="file" accept=".csv, .xlsx, .xls" onChange={handleFileUpload} className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          <p className={`mt-2 text-sm font-medium ${isUploaded ? 'text-green-700 font-bold' : 'text-red-600'}`}>{uploadStatus}</p>
        </div>

        {/* Search Zone */}
        <div className="bg-gray-100 p-6 rounded-lg shadow relative">
          <h2 className="text-xl font-semibold mb-4">Tìm kiếm học phần</h2>
          <input type="text" value={searchQuery} onChange={handleSearchChange} disabled={!isUploaded} placeholder={isUploaded ? "Nhập tên hoặc mã học phần..." : "Vui lòng tải file lên trước..."} className="w-full border p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-200" />
          
          {suggestions.length > 0 && (
            <ul className="absolute z-10 w-full bg-white border border-gray-300 rounded mt-1 shadow-lg max-h-60 overflow-y-auto">
              {suggestions.map(c => (
                <li key={c.ma_hp} onClick={() => openClassModal(c.ma_hp, c.ten_hp)} className="p-3 hover:bg-blue-50 cursor-pointer border-b text-sm font-semibold text-gray-700">
                  {c.ma_hp} - {c.ten_hp}
                </li>
              ))}
            </ul>
          )}

          <div className="mt-4">
            <h3 className="font-medium text-gray-700">Các học phần đã chọn :</h3>
            <ul className="flex flex-wrap gap-3 mt-3">
              {Object.entries(selectedCourses).map(([ma, info]) => (
                <li key={ma} className="bg-green-100 border border-green-500 text-green-900 text-sm font-bold px-4 py-2 rounded-lg flex items-center shadow-sm hover:bg-green-200 cursor-pointer transition" onClick={() => openClassModal(ma, info.ten_hp)}>
                  <span>{ma} - {info.ten_hp}</span>
                  <button onClick={(e) => { e.stopPropagation(); removeCourse(ma); }} className="ml-3 text-red-500 hover:text-red-700 text-2xl leading-none font-bold">×</button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Busy Grid */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Chọn ngày muốn nghỉ</h2>
          <table className="w-full text-center border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2">Buổi</th>
                {DAYS.map(d => <th key={d} className="border p-2">{d === 'CN' ? 'CN' : `T${d}`}</th>)}
              </tr>
            </thead>
            <tbody>
              {['sáng', 'chiều'].map(buoi => (
                <tr key={buoi}>
                  <td className="border p-2 font-medium capitalize">{buoi}</td>
                  {DAYS.map(d => {
                    const isChecked = busySlots.some(b => b.thu === d && b.buoi === buoi);
                    return (
                      <td key={`${d}-${buoi}`} className="border p-2">
                        <input type="checkbox" checked={isChecked} onChange={() => handleBusyToggle(d, buoi)} className="w-5 h-5 accent-gray-600" />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <button onClick={generateSchedules} disabled={!isUploaded} className="w-full bg-blue-600 disabled:bg-gray-400 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded shadow-lg text-lg">
          Tạo Thời Khóa Biểu
        </button>
      </div>

      {/* Modal Chọn Lớp */}
      {modalData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-[650px] max-w-full shadow-2xl">
            <h3 className="text-xl font-bold mb-4">Tổ hợp lớp: {modalData.ma_hp} - {modalData.ten_hp}</h3>
            
            <div className="max-h-[60vh] overflow-y-auto mb-4 p-2">
              {/* Render Tổ hợp đại diện & kèm */}
              {modalData.bundles.map((b, idx) => {
                const ddChecked = tempTickedClasses.has(b.dai_dien.ma_lop);
                return (
                  <div key={idx} className="bg-green-50 border border-green-300 rounded-lg p-4 mb-4">
                    <label className="flex items-start cursor-pointer text-gray-800 text-lg">
                      <input type="checkbox" checked={ddChecked} onChange={() => toggleClassTick(b.dai_dien.ma_lop)} className="mr-3 mt-[6px] w-5 h-5 accent-green-600" />
                      <div>
                        <span className="font-bold">{b.dai_dien.ma_lop} • Loại: {b.dai_dien.loai_lop}</span><br/>
                        <span className="text-sm font-semibold text-blue-600">T{b.dai_dien.thu} • {b.dai_dien.thoi_gian}</span>
                      </div>
                    </label>
                    {b.kems.length > 0 && (
                      <div className="flex flex-wrap gap-3 mt-3 ml-8">
                        {b.kems.map(k => (
                          <label key={k.ma_lop} className="border-2 border-gray-700 rounded-lg p-2 bg-transparent min-w-[150px] flex flex-col cursor-pointer">
                            <div className="flex items-center text-sm font-bold text-gray-800">
                              <input type="checkbox" checked={tempTickedClasses.has(k.ma_lop)} onChange={() => toggleClassTick(k.ma_lop)} className="mr-2 accent-green-600" />
                              {k.ma_lop} • {k.loai_lop}
                            </div>
                            <span className="text-xs font-semibold text-blue-500 mt-1 ml-5">T{k.thu} • {k.thoi_gian}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Render Lớp Thí Nghiệm */}
              {modalData.labs.length > 0 && (
                <>
                  <h4 className="font-bold text-red-600 mb-2 mt-4">Lớp Thí Nghiệm</h4>
                  <div className="flex flex-wrap gap-2">
                    {modalData.labs.map(lb => (
                      <label key={lb.ma_lop} className="border-2 border-red-200 bg-red-50 p-2 rounded cursor-pointer flex flex-col text-sm w-fit">
                        <div className="font-bold">
                          <input type="checkbox" checked={tempTickedClasses.has(lb.ma_lop)} onChange={() => toggleClassTick(lb.ma_lop)} className="mr-1 accent-red-600" />
                          {lb.ma_lop}
                        </div>
                        <span className="text-xs text-red-500 ml-4">T{lb.thu} • {lb.thoi_gian}</span>
                      </label>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div className="flex justify-end space-x-2 border-t pt-4">
              <button onClick={() => setModalData(null)} className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400 font-bold">Hủy</button>
              <button onClick={confirmClassSelection} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-bold">Lưu</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}