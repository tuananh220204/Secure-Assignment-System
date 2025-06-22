import socket
import json
import base64
import os
import threading
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from config import Config
from crypto_utils import CryptoUtils
from database import Database

class AssignmentReceiver:
    def __init__(self):
        self.config = Config()
        self.crypto = CryptoUtils(
            private_key_path=self.config.PRIVATE_KEY_PATH,
            public_key_path=self.config.PUBLIC_KEY_PATH
        )
        self.db = Database()
        self.socket = None
        self.running = False
        
        # Tạo keys nếu chưa có
        if not self.config.PRIVATE_KEY_PATH.exists():
            print("Tạo cặp khóa RSA...")
            self.crypto.generate_rsa_keys()
            print(f"Khóa đã được tạo tại: {self.config.KEYS_DIR}")
    
    def start_server(self, host=None, port=None):
        """Khởi động server"""
        host = host or self.config.HOST
        port = port or self.config.PORT
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(5)
        
        self.running = True
        print(f"Server đang lắng nghe tại {host}:{port}")
        self.db.log_action("SERVER_START", f"Server started at {host}:{port}")
        
        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                print(f"Kết nối từ {client_address}")
                
                # Xử lý client trong thread riêng
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"Lỗi server: {e}")
                    self.db.log_action("SERVER_ERROR", str(e), status='error')
    
    def handle_client(self, client_socket, client_address):
        """Xử lý một client"""
        session_key = None
        file_parts = {}
        current_file_id = None
        file_hash_expected = None
        filename = None
        
        try:
            # Handshake
            hello_msg = client_socket.recv(1024).decode('utf-8')
            if hello_msg == "Hello!":
                client_socket.send(b"Ready!")
                print(f"Handshake thành công với {client_address}")
            else:
                client_socket.send(b"ERROR")
                client_socket.close()
                return
            
            while True:
                # Nhận độ dài dữ liệu
                length_data = client_socket.recv(4)
                if not length_data:
                    break
                
                data_length = int.from_bytes(length_data, 'big')
                
                # Nhận dữ liệu
                data = b""
                while len(data) < data_length:
                    chunk = client_socket.recv(min(data_length - len(data), self.config.BUFFER_SIZE))
                    if not chunk:
                        break
                    data += chunk
                
                if not data:
                    break
                
                try:
                    packet = json.loads(data.decode('utf-8'))
                    
                    # Xử lý auth packet
                    if "metadata" in packet and "session_key" in packet:
                        if self.handle_auth_packet(packet, client_socket):
                            session_key = self.decrypt_session_key(packet["session_key"])
                            metadata = packet["metadata"]
                            filename = metadata["filename"]
                            file_hash_expected = metadata.get("file_hash")
                            current_file_id = self.db.create_file_record(
                                filename,
                                0,  # Sẽ cập nhật sau
                                {"sender_address": str(client_address), "timestamp": metadata["timestamp"]}
                            )
                            
                            print(f"Tạo file record ID: {current_file_id}")
                        else:
                            break
                    
                    # Xử lý part packet
                    elif "part_id" in packet and session_key:
                        if self.handle_part_packet(packet, session_key, client_socket, current_file_id, file_parts):
                            total_parts = packet["total_parts"]
                            if len(file_parts) == total_parts:
                                if self.reconstruct_file(file_parts, filename, current_file_id, file_hash_expected):
                                    client_socket.send(b"COMPLETE")
                                    print("File đã được tái tạo thành công!")
                                else:
                                    client_socket.send(b"RECONSTRUCT_ERROR")
                                break
                        
                except json.JSONDecodeError as e:
                    print(f"Lỗi JSON: {e}")
                    client_socket.send(b"JSON_ERROR")
                    break
                    
        except Exception as e:
            print(f"Lỗi xử lý client {client_address}: {e}")
            self.db.log_action("CLIENT_ERROR", str(e), str(client_address), status='error')
        
        finally:
            client_socket.close()
            print(f"Đã đóng kết nối với {client_address}")
    
    def handle_auth_packet(self, packet, client_socket):
        """Xử lý gói xác thực"""
        try:
            metadata = packet["metadata"]
            signature = base64.b64decode(packet["signature"])
            
            # Xác thực chữ ký metadata
            metadata_str = json.dumps(metadata)
            if self.crypto.rsa_verify(metadata_str, signature):
                client_socket.send(b"AUTH_OK")
                print("Xác thực metadata thành công!")
                self.db.log_action("AUTH_SUCCESS", f"Metadata verified for {metadata['filename']}")
                return True
            else:
                client_socket.send(b"AUTH_FAILED")
                print("Xác thực metadata thất bại!")
                self.db.log_action("AUTH_FAILED", f"Metadata verification failed", status='error')
                return False
                
        except Exception as e:
            print(f"Lỗi xác thực: {e}")
            client_socket.send(b"AUTH_ERROR")
            return False
    
    def decrypt_session_key(self, encrypted_session_key_b64):
        """Giải mã session key"""
        try:
            encrypted_session_key = base64.b64decode(encrypted_session_key_b64)
            session_key = self.crypto.rsa_decrypt(encrypted_session_key)
            return session_key
        except Exception as e:
            print(f"Lỗi giải mã session key: {e}")
            return None
    
    def handle_part_packet(self, packet, session_key, client_socket, file_id, file_parts):
        """Xử lý gói phần file"""
        try:
            part_id = packet["part_id"]
            iv = base64.b64decode(packet["iv"])
            ciphertext = base64.b64decode(packet["cipher"])
            received_hash = packet["hash"]
            signature = base64.b64decode(packet["sig"])
            
            # Kiểm tra hash
            hash_data = iv + ciphertext
            calculated_hash = self.crypto.calculate_hash(hash_data)
            
            if calculated_hash != received_hash:
                print(f"Hash không khớp cho phần {part_id}")
                client_socket.send(b"NACK")
                return False
            
            # Kiểm tra chữ ký
            part_info = f"{part_id}:{packet['filename']}:{received_hash}"
            if not self.crypto.rsa_verify(part_info, signature):
                print(f"Chữ ký không hợp lệ cho phần {part_id}")
                client_socket.send(b"NACK")
                return False
            
            # Giải mã phần file
            decrypted_data = self.crypto.des_decrypt(iv, ciphertext, session_key)
            
            # Lưu phần file
            file_parts[part_id] = decrypted_data
            
            # Cập nhật database
            if file_id:
                self.db.update_file_part(file_id, part_id, received_hash, base64.b64encode(signature).decode('utf-8'))
            
            print(f"Nhận phần {part_id} thành công!")
            client_socket.send(b"ACK")
            return True
            
        except Exception as e:
            print(f"Lỗi xử lý phần file: {e}")
            client_socket.send(b"NACK")
            return False
    
    def reconstruct_file(self, file_parts, filename, file_id, file_hash_expected=None):
        """Tái tạo file từ các phần và kiểm tra hash nếu có"""
        try:
            # Sắp xếp các phần theo thứ tự
            sorted_parts = []
            for i in range(1, len(file_parts) + 1):
                if i in file_parts:
                    sorted_parts.append(file_parts[i])
                else:
                    print(f"Thiếu phần {i}")
                    return False
            
            # Ghép các phần lại
            complete_data = b"".join(sorted_parts)
            
            print(f"Số phần nhận được: {len(file_parts)}")
            for i, part in file_parts.items():
                print(f"Phần {i}: {len(part)} bytes")
            print(f"Tổng kích thước sau khi ghép: {len(complete_data)} bytes")
            
            # Kiểm tra hash nếu có
            if file_hash_expected:
                import hashlib
                file_hash_actual = hashlib.sha512(complete_data).hexdigest()
                if file_hash_actual != file_hash_expected:
                    print(f"Hash file không khớp!\nExpected: {file_hash_expected}\nActual:   {file_hash_actual}")
                    self.db.log_action("HASH_MISMATCH", f"File {filename} hash mismatch", status='error')
                    return False
            
            # Lưu file
            output_path = self.config.RECEIVED_FILES_DIR / filename
            with open(output_path, 'wb') as f:
                f.write(complete_data)
            
            # Cập nhật database với kích thước thực tế
            if file_id:
                file_size = len(complete_data)
                print(f"[DEBUG] file_id: {file_id}, file_size: {file_size}")
                self.db.update_file_size(file_id, file_size)
                print("[DEBUG] Đã cập nhật kích thước file trong database.")
                self.db.complete_file(file_id)
            
            print(f"File đã được lưu tại: {output_path}")
            self.db.log_action("FILE_RECONSTRUCTED", f"File {filename} reconstructed successfully")
            return True
            
        except Exception as e:
            print(f"Lỗi tái tạo file: {e}")
            self.db.log_action("RECONSTRUCT_ERROR", str(e), status='error')
            return False
    
    def stop_server(self):
        """Dừng server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print("Server đã dừng!")