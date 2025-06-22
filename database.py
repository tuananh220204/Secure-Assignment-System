import sqlite3
import json
from datetime import datetime
from config import Config
from zoneinfo import ZoneInfo

class Database:
    def __init__(self, db_path=Config.DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Khởi tạo cơ sở dữ liệu"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Bảng users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bảng files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_size INTEGER,
                total_parts INTEGER DEFAULT 3,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                sender_info TEXT
            )
        ''')
        
        # Bảng file_parts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                part_id INTEGER,
                hash_value TEXT,
                signature TEXT,
                status TEXT DEFAULT 'pending',
                received_at TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files (id)
            )
        ''')
        
        # Bảng logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                status TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_file_record(self, filename, original_size, sender_info=None):
        """Tạo bản ghi file mới"""
        conn = self.get_connection()
        cursor = conn.cursor()
        from zoneinfo import ZoneInfo
        created_at = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        cursor.execute('''
            INSERT INTO files (filename, original_size, sender_info, created_at)
            VALUES (?, ?, ?, ?)
        ''', (filename, original_size, json.dumps(sender_info) if sender_info else None, created_at))
        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_id
    
    def update_file_part(self, file_id, part_id, hash_value, signature, status='received'):
        """Cập nhật trạng thái phần file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO file_parts 
            (file_id, part_id, hash_value, signature, status, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            file_id, part_id, hash_value, signature, status, 
            datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        ))
        
        conn.commit()
        conn.close()
    
    def complete_file(self, file_id):
        """Đánh dấu file hoàn thành"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE files SET status = 'completed', completed_at = ?
            WHERE id = ?
        ''', (
            datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")), file_id
        ))
        
        conn.commit()
        conn.close()
    
    def log_action(self, action, details, ip_address=None, status='success'):
        """Ghi log hành động"""
        conn = self.get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        cursor.execute('''
            INSERT INTO logs (action, details, timestamp, ip_address, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (action, details, timestamp, ip_address, status))
        conn.commit()
        conn.close()
    
    def get_files(self, limit=50):
        """Lấy danh sách file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, original_size, total_parts, status, 
                   created_at, completed_at, sender_info
            FROM files 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        files = cursor.fetchall()
        conn.close()
        
        return files
    
    def get_logs(self, limit=100):
        """Lấy logs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action, details, timestamp, ip_address, status
            FROM logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        logs = cursor.fetchall()
        conn.close()
        
        return logs
    
    def update_file_size(self, file_id, file_size):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE files SET original_size = ? WHERE id = ?', (file_size, file_id))
        conn.commit()
        conn.close()