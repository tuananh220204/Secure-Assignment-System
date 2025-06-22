from flask import Flask, request, render_template, jsonify, send_from_directory, flash, redirect, url_for
import os
import json
import threading
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from database import Database
from sender import AssignmentSender
from receiver import AssignmentReceiver
import sys

# Xử lý timezone an toàn
try:
    from zoneinfo import ZoneInfo
    def get_timezone():
        try:
            return ZoneInfo("Asia/Ho_Chi_Minh")
        except:
            return None
except ImportError:
    def get_timezone():
        return None

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
from flask_moment import Moment
moment = Moment(app)
db = Database()
receiver_instance = None
receiver_thread = None

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('base.html')

@app.route('/sender')
def sender_page():
    """Trang gửi file"""
    return render_template('sender.html')

@app.route('/receiver')
def receiver_page():
    """Trang nhận file"""
    return render_template('receiver.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard hệ thống"""
    files = db.get_files(20)
    logs = db.get_logs(50)
    
    # Xử lý timezone an toàn
    tz = get_timezone()
    if tz:
        today = datetime.now(tz).strftime("%Y-%m-%d")
    else:
        today = datetime.now().strftime("%Y-%m-%d")
    
    return render_template('dashboard.html', files=files, logs=logs, today=today)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload và gửi file"""
    if 'file' not in request.files:
        return jsonify({'error': 'Không có file được chọn'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Không có file được chọn'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Gửi file
        host = request.form.get('host', 'localhost')
        port = int(request.form.get('port', 8888))
        
        sender = AssignmentSender()
        success, warning = sender.send_file(filepath)
        if success:
            return jsonify({'message': 'File đã được gửi thành công!', 'filename': filename, 'warning': warning})
        else:
            return jsonify({'error': 'Gửi file thất bại! Không thể kết nối tới receiver hoặc lỗi khi gửi.', 'warning': warning}), 500

@app.route('/start_receiver', methods=['POST'])
def start_receiver():
    """Khởi động receiver server"""
    global receiver_instance, receiver_thread
    
    if receiver_instance and receiver_instance.running:
        return jsonify({'error': 'Server đã đang chạy!'}), 400
    
    host = request.json.get('host', 'localhost')
    port = int(request.json.get('port', 8888))
    
    receiver_instance = AssignmentReceiver()
    receiver_thread = threading.Thread(
        target=receiver_instance.start_server,
        args=(host, port)
    )
    receiver_thread.daemon = True
    receiver_thread.start()
    
    return jsonify({'message': f'Server đã khởi động tại {host}:{port}'})

@app.route('/stop_receiver', methods=['POST'])
def stop_receiver():
    """Dừng receiver server"""
    global receiver_instance
    
    if receiver_instance:
        receiver_instance.stop_server()
        return jsonify({'message': 'Server đã dừng!'})
    else:
        return jsonify({'error': 'Server chưa được khởi động!'}), 400

@app.route('/api/files')
def api_files():
    """API lấy danh sách files"""
    files = db.get_files(50)
    files_data = []
    
    for file_info in files:
        files_data.append({
            'id': file_info[0],
            'filename': file_info[1],
            'size': file_info[2],
            'parts': file_info[3],
            'status': file_info[4],
            'created_at': file_info[5].isoformat() if hasattr(file_info[5], 'isoformat') else file_info[5],
            'completed_at': file_info[6].isoformat() if file_info[6] and hasattr(file_info[6], 'isoformat') else file_info[6]
        })
    
    return jsonify(files_data)

@app.route('/api/logs')
def api_logs():
    """API lấy logs"""
    logs = db.get_logs(100)
    logs_data = []
    
    for log in logs:
        logs_data.append({
            'action': log[0],
            'details': log[1],
            'timestamp': log[2].isoformat() if hasattr(log[2], 'isoformat') else log[2],
            'ip_address': log[3],
            'status': log[4]
        })
    
    return jsonify(logs_data)

@app.route('/api/file/<int:file_id>')
def api_file_detail(file_id):
    """API lấy chi tiết file theo id"""
    file = None
    # Lấy file từ database
    files = db.get_files(1000)  # lấy nhiều để tìm
    for f in files:
        if f[0] == file_id:
            file = f
            break
    if not file:
        return jsonify({'error': 'Không tìm thấy file!'}), 404
    # Giải mã metadata nếu có
    metadata = None
    try:
        if file[7]:
            import json
            metadata = json.loads(file[7])
    except Exception:
        metadata = file[7]
    return jsonify({
        'id': file[0],
        'filename': file[1],
        'size': file[2],
        'parts': file[3],
        'status': file[4],
        'created_at': file[5].isoformat() if hasattr(file[5], 'isoformat') else file[5],
        'completed_at': file[6].isoformat() if file[6] and hasattr(file[6], 'isoformat') else file[6],
        'metadata': metadata
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Download file đã nhận"""
    file_path = os.path.join(str(Config.RECEIVED_FILES_DIR), filename)
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return f"File {filename} không tồn tại hoặc rỗng!", 404
    return send_from_directory(Config.RECEIVED_FILES_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)