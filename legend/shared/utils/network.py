import socket
from typing import Optional


def get_available_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
    """查找可用端口
    
    从start_port开始，尝试查找可用端口，最多尝试max_attempts次
    
    Args:
        start_port: 起始端口号
        max_attempts: 最大尝试次数
        
    Returns:
        Optional[int]: 可用端口号，如果未找到则返回None
    """
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return None
