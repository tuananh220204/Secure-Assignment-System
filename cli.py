import click
import os
from sender import AssignmentSender
from receiver import AssignmentReceiver
from config import Config

@click.group()
def cli():
    """Hệ thống gửi bài tập chia thành nhiều phần an toàn"""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--host', default='localhost', help='Địa chỉ server')
@click.option('--port', default=8888, help='Port server')
def send(file_path, host, port):
    """Gửi file bài tập"""
    click.echo(f"Đang gửi file: {file_path}")
    
    sender = AssignmentSender()
    
    if sender.connect_to_receiver(host, port):
        success = sender.send_file(file_path)
        if success:
            click.echo("✅ Gửi file thành công!")
        else:
            click.echo("❌ Gửi file thất bại!")
    else:
        click.echo("❌ Không thể kết nối đến server!")
    
    sender.disconnect()

@cli.command()
@click.option('--host', default='localhost', help='Địa chỉ bind server')
@click.option('--port', default=8888, help='Port bind server')
def receive(host, port):
    """Khởi động server nhận file"""
    click.echo(f"Khởi động server tại {host}:{port}")
    
    receiver = AssignmentReceiver()
    
    try:
        receiver.start_server(host, port)
    except KeyboardInterrupt:
        click.echo("\n🛑 Dừng server...")
        receiver.stop_server()

@cli.command()
def generate_keys():
    """Tạo cặp khóa RSA mới"""
    from crypto_utils import CryptoUtils
    
    config = Config()
    crypto = CryptoUtils(
        private_key_path=config.PRIVATE_KEY_PATH,
        public_key_path=config.PUBLIC_KEY_PATH
    )
    
    crypto.generate_rsa_keys()
    click.echo(f"✅ Đã tạo cặp khóa RSA tại: {config.KEYS_DIR}")

@cli.command()
def status():
    """Hiển thị trạng thái hệ thống"""
    from database import Database
    
    db = Database()
    
    # Hiển thị files
    files = db.get_files(10)
    click.echo("📁 Files gần đây:")
    for file_info in files:
        click.echo(f"  - {file_info[1]} ({file_info[4]}) - {file_info[5]}")
    
    # Hiển thị logs
    logs = db.get_logs(5)
    click.echo("\n📋 Logs gần đây:")
    for log in logs:
        click.echo(f"  - {log[2]}: {log[0]} - {log[4]}")

if __name__ == '__main__':
    cli()