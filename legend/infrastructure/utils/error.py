"""错误处理工具"""

import sys
import traceback
from typing import Optional


def format_error_detail(exc_info: Optional[tuple] = None) -> str:
    """格式化错误详情
    
    Args:
        exc_info: 异常信息元组，默认使用 sys.exc_info()
        
    Returns:
        str: 格式化后的错误详情
    """
    if exc_info is None:
        exc_info = sys.exc_info()
        
    if not any(exc_info):
        return "No error information available"
        
    # 获取完整的错误堆栈
    tb_lines = traceback.format_exception(*exc_info)
    
    # 获取最后一个错误位置
    last_frame = traceback.extract_tb(exc_info[2])[-1]
    
    error_detail = (
        f"错误类型: {exc_info[0].__name__}\n"
        f"错误信息: {str(exc_info[1])}\n"
        f"错误位置: 文件 {last_frame.filename}, 行 {last_frame.lineno}, 在 {last_frame.name}\n"
        f"错误堆栈:\n{''.join(tb_lines)}"
    )
    
    return error_detail 