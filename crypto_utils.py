import os
import hashlib
import base64
import json
from datetime import datetime
from Crypto.Cipher import DES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA512
from Crypto.Signature import pkcs1_15
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import logging

class CryptoUtils:
    def __init__(self, private_key_path=None, public_key_path=None):
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self.private_key = None
        self.public_key = None
        
        if private_key_path and os.path.exists(private_key_path):
            self.load_private_key()
        if public_key_path and os.path.exists(public_key_path):
            self.load_public_key()
    
    def generate_rsa_keys(self):
        """Tạo cặp khóa RSA 1024-bit"""
        key = RSA.generate(1024)
        
        # Lưu private key
        with open(self.private_key_path, 'wb') as f:
            f.write(key.export_key())
        
        # Lưu public key
        with open(self.public_key_path, 'wb') as f:
            f.write(key.publickey().export_key())
        
        self.private_key = key
        self.public_key = key.publickey()
        
        return key, key.publickey()
    
    def load_private_key(self):
        """Load private key từ file"""
        with open(self.private_key_path, 'rb') as f:
            self.private_key = RSA.import_key(f.read())
    
    def load_public_key(self):
        """Load public key từ file"""
        with open(self.public_key_path, 'rb') as f:
            self.public_key = RSA.import_key(f.read())
    
    def generate_des_key(self):
        """Tạo khóa DES ngẫu nhiên 8 bytes"""
        return get_random_bytes(8)
    
    def rsa_encrypt(self, data, public_key=None):
        """Mã hóa dữ liệu bằng RSA (PKCS#1 v1.5)"""
        if public_key is None:
            public_key = self.public_key
        
        cipher = PKCS1_v1_5.new(public_key)
        return cipher.encrypt(data)
    
    def rsa_decrypt(self, ciphertext, private_key=None):
        """Giải mã dữ liệu bằng RSA"""
        if private_key is None:
            private_key = self.private_key
        
        cipher = PKCS1_v1_5.new(private_key)
        return cipher.decrypt(ciphertext, None)
    
    def rsa_sign(self, message, private_key=None):
        """Ký số bằng RSA/SHA-512"""
        if private_key is None:
            private_key = self.private_key
        
        hash_obj = SHA512.new()
        if isinstance(message, str):
            message = message.encode('utf-8')
        hash_obj.update(message)
        
        signature = pkcs1_15.new(private_key).sign(hash_obj)
        return signature
    
    def rsa_verify(self, message, signature, public_key=None):
        """Xác thực chữ ký RSA/SHA-512"""
        if public_key is None:
            public_key = self.public_key
        
        hash_obj = SHA512.new()
        if isinstance(message, str):
            message = message.encode('utf-8')
        hash_obj.update(message)
        
        try:
            pkcs1_15.new(public_key).verify(hash_obj, signature)
            return True
        except (ValueError, TypeError):
            return False
    
    def des_encrypt(self, data, key):
        """Mã hóa dữ liệu bằng DES"""
        cipher = DES.new(key, DES.MODE_CBC)
        iv = cipher.iv
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Padding dữ liệu
        padded_data = pad(data, DES.block_size)
        ciphertext = cipher.encrypt(padded_data)
        
        return iv, ciphertext
    
    def des_decrypt(self, iv, ciphertext, key):
        """Giải mã dữ liệu bằng DES"""
        cipher = DES.new(key, DES.MODE_CBC, iv=iv)
        padded_data = cipher.decrypt(ciphertext)
        
        # Unpadding
        data = unpad(padded_data, DES.block_size)
        return data
    
    def calculate_hash(self, data):
        """Tính hash SHA-512"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha512(data).hexdigest()
    
    def split_file(self, file_path, num_parts=3):
        with open(file_path, 'rb') as f:
            content = f.read()
        file_size = len(content)
        warning = None
        if file_size == 0:
            warning = 'File rỗng!'
            return [b''] * num_parts, warning
        if file_size < num_parts:
            warning = f'File quá nhỏ để chia thành {num_parts} phần. Mỗi phần sẽ chỉ có 1 byte, phần dư sẽ rỗng.'
            parts = [content[i:i+1] for i in range(file_size)]
            parts += [b''] * (num_parts - file_size)
            return parts, warning
        part_size = file_size // num_parts
        parts = []
        for i in range(num_parts):
            start = i * part_size
            if i == num_parts - 1:
                end = file_size
            else:
                end = (i + 1) * part_size
            parts.append(content[start:end])
        return parts, warning