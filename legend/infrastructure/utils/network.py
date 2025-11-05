"""网络工具函数"""

import socket
from typing import Optional


def find_available_port(
    start_port: int = 8000,
    max_attempts: int = 100,
    host: str = "127.0.0.1"
) -> Optional[int]:
    """查找可用的端口号
    
    Args:
        start_port: 起始端口号
        max_attempts: 最大尝试次数
        host: 主机地址
        
    Returns:
        Optional[int]: 可用的端口号，如果未找到则返回None
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # 设置端口重用
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # 尝试绑定端口
                sock.bind((host, port))
                return port
        except OSError:
            continue
            
    return None


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否被占用
    
    Args:
        port: 端口号
        host: 主机地址
        
    Returns:
        bool: 端口是否被占用
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except OSError:
        return True 