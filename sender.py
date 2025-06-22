import socket
import json
import base64
import logging
from datetime import datetime
from config import Config
from crypto_utils import CryptoUtils
from database import Database
import os
from zoneinfo import ZoneInfo

class AssignmentSender:
    def __init__(self):
        self.config = Config()
        self.crypto = CryptoUtils(
            private_key_path=self.config.PRIVATE_KEY_PATH,
            public_key_path=self.config.PUBLIC_KEY_PATH
        )
        self.db = Database()
        self.session_key = None
        self.socket = None
        
        # Tạo keys nếu chưa có
        if not self.config.PRIVATE_KEY_PATH.exists():
            print("Tạo cặp khóa RSA...")
            self.crypto.generate_rsa_keys()
            print(f"Khóa đã được tạo tại: {self.config.KEYS_DIR}")
    
    def connect_to_receiver(self, host=None, port=None):
        """Kết nối đến receiver"""
        host = host or self.config.HOST
        port = port or self.config.PORT
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # Handshake
            self.socket.send(b"Hello!")
            response = self.socket.recv(1024).decode('utf-8')
            
            if response == "Ready!":
                print("Kết nối thành công!")
                self.db.log_action("CONNECT", f"Connected to {host}:{port}")
                return True
            else:
                print(f"Handshake thất bại: {response}")
                return False
                
        except Exception as e:
            print(f"Lỗi kết nối: {e}")
            self.db.log_action("CONNECT_ERROR", str(e), status='error')
            return False
    
    def send_metadata_and_key(self, filename, total_parts, file_hash=None):
        """Gửi metadata và session key"""
        # Tạo session key cho DES
        self.session_key = self.crypto.generate_des_key()
        
        # Tạo metadata
        metadata = {
            "filename": filename,
            "timestamp": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
            "total_parts": total_parts,
            "sender": "assignment_sender"
        }
        if file_hash:
            metadata["file_hash"] = file_hash
        
        metadata_str = json.dumps(metadata)
        
        # Ký metadata
        signature = self.crypto.rsa_sign(metadata_str)
        
        # Mã hóa session key bằng RSA
        encrypted_session_key = self.crypto.rsa_encrypt(self.session_key)
        
        # Tạo gói tin auth
        auth_packet = {
            "metadata": metadata,
            "signature": base64.b64encode(signature).decode('utf-8'),
            "session_key": base64.b64encode(encrypted_session_key).decode('utf-8')
        }
        
        # Gửi auth packet
        auth_data = json.dumps(auth_packet).encode('utf-8')
        self.socket.send(len(auth_data).to_bytes(4, 'big'))  # Gửi độ dài trước
        self.socket.send(auth_data)
        
        # Nhận phản hồi
        response = self.socket.recv(1024).decode('utf-8')
        if response == "AUTH_OK":
            print("Xác thực thành công!")
            return True
        else:
            print(f"Xác thực thất bại: {response}")
            return False
    
    def send_file_part(self, part_data, part_id, filename, total_parts):
        """Gửi một phần file"""
        # Mã hóa phần file bằng DES
        iv, ciphertext = self.crypto.des_encrypt(part_data, self.session_key)
        
        # Tính hash của IV || ciphertext
        hash_data = iv + ciphertext
        hash_value = self.crypto.calculate_hash(hash_data)
        
        # Ký phần này
        part_info = f"{part_id}:{filename}:{hash_value}"
        signature = self.crypto.rsa_sign(part_info)
        
        # Tạo gói tin part
        part_packet = {
            "part_id": part_id,
            "total_parts": total_parts,
            "filename": filename,
            "iv": base64.b64encode(iv).decode('utf-8'),
            "cipher": base64.b64encode(ciphertext).decode('utf-8'),
            "hash": hash_value,
            "sig": base64.b64encode(signature).decode('utf-8')
        }
        
        # Gửi part packet
        part_data = json.dumps(part_packet).encode('utf-8')
        self.socket.send(len(part_data).to_bytes(4, 'big'))
        self.socket.send(part_data)
        
        # Nhận phản hồi
        response = self.socket.recv(1024).decode('utf-8')
        
        if response == "ACK":
            print(f"Phần {part_id} đã gửi thành công!")
            return True
        elif response == "NACK":
            print(f"Phần {part_id} bị lỗi, cần gửi lại!")
            return False
        else:
            print(f"Phản hồi không xác định: {response}")
            return False
    
    def send_file(self, file_path):
        """Gửi toàn bộ file"""
        try:
            parts, warning = self.crypto.split_file(file_path, self.config.TOTAL_PARTS)
            filename = os.path.basename(file_path)

            # Kết nối tới receiver trước khi gửi
            if not self.connect_to_receiver():
                print("Không thể kết nối tới receiver!")
                return False, warning

            # Tính hash tổng thể file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            file_hash = self.crypto.calculate_hash(file_data)

            if warning:
                print(f"[CẢNH BÁO] {warning}")

            print(f"Chia file '{filename}' thành {len(parts)} phần")
            
            # Gửi metadata và session key (bổ sung file_hash)
            if not self.send_metadata_and_key(filename, len(parts), file_hash):
                return False, warning
            
            # Gửi từng phần
            for i, part_data in enumerate(parts, 1):
                print(f"Đang gửi phần {i}/{len(parts)}...")
                
                success = False
                retries = 3
                
                while not success and retries > 0:
                    success = self.send_file_part(part_data, i, filename, len(parts))
                    if not success:
                        retries -= 1
                        print(f"Thử lại... (còn {retries} lần)")
                
                if not success:
                    print(f"Không thể gửi phần {i} sau 3 lần thử!")
                    return False, warning
            
            # Nhận phản hồi cuối cùng
            final_response = self.socket.recv(1024).decode('utf-8')
            if final_response == "COMPLETE":
                print("Gửi file hoàn tất!")
                self.db.log_action("SEND_COMPLETE", f"File {filename} sent successfully")
                return True, warning
            else:
                print(f"Lỗi cuối cùng: {final_response}")
                return False, warning
                
        except Exception as e:
            print(f"Lỗi khi gửi file: {e}")
            self.db.log_action("SEND_ERROR", str(e), status='error')
            return False, warning
    
    def disconnect(self):
        """Ngắt kết nối"""
        if self.socket:
            self.socket.close()
            print("Đã ngắt kết nối!")