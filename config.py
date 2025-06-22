import os
from pathlib import Path

class Config:
    # Đường dẫn dự án
    PROJECT_ROOT = Path(__file__).parent
    KEYS_DIR = PROJECT_ROOT / "keys"
    LOGS_DIR = PROJECT_ROOT / "logs"
    DATA_DIR = PROJECT_ROOT / "data"
    RECEIVED_FILES_DIR = DATA_DIR / "received_files"
    
    # Tạo thư mục nếu chưa tồn tại
    for dir_path in [KEYS_DIR, LOGS_DIR, DATA_DIR, RECEIVED_FILES_DIR]:
        dir_path.mkdir(exist_ok=True)
    
    # Cấu hình mạng
    HOST = "localhost"
    PORT = 8888
    BUFFER_SIZE = 4096
    
    # Cấu hình bảo mật
    RSA_KEY_SIZE = 1024
    DES_KEY_SIZE = 8  # 8 bytes = 64 bits
    TOTAL_PARTS = 3
    
    # Đường dẫn khóa
    PRIVATE_KEY_PATH = KEYS_DIR / "private_key.pem"
    PUBLIC_KEY_PATH = KEYS_DIR / "public_key.pem"
    
    # Database
    DATABASE_PATH = DATA_DIR / "assignment_system.db"
    
    # Web config
    SECRET_KEY = "your-secret-key-here"
    UPLOAD_FOLDER = DATA_DIR / "uploads"
    UPLOAD_FOLDER.mkdir(exist_ok=True)