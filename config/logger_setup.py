import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

def setup_logger(name: str) -> logging.Logger:
    """
    Tạo và cấu hình logger tập trung cho module.
    Đa kênh: Console & File (có xoay vòng rotating).
    """
    logger = logging.getLogger(name)
    
    # Nếu logger đã có handler thì không add thêm để tránh duplicate log
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Đảm bảo thư mục logs tồn tại
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "omega_apex.log"

    # Format chuẩn
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
    )

    # 1. Console Handler (In ra màn hình)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Trên console chỉ hiện từ INFO trở lên cho đỡ rác
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (Lưu ra file, tối đa 10MB/file, giữ lại 5 file cũ)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG) # Ghi tất cả vào file để debug
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
