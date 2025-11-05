"""SQL安全验证器实现"""

import logging
import re
from typing import Any, Dict, List, Optional, Pattern

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """安全违规错误"""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class SQLSecurityValidator:
    """SQL安全验证器"""
    
    def __init__(self) -> None:
        """初始化安全验证器"""
        # SQL注入模式
        self._sql_injection_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                r";\s*drop\s+table",  # 删除表
                r";\s*delete\s+from",  # 删除数据
                r";\s*truncate\s+table",  # 截断表
                r";\s*alter\s+table",  # 修改表结构
                r";\s*update\s+.*set",  # 更新数据
                r";\s*insert\s+into",  # 插入数据
                r"union\s+select",  # UNION注入
                r"--",  # 注释
                r"/\*.*\*/",  # 多行注释
                r"xp_cmdshell",  # 命令执行
                r"exec\s+\w+",  # 存储过程执行
                r"declare\s+@",  # 变量声明
                r"select.*from.*where.*=.*1\s*=\s*1",  # 永真条件
            ]
        ]
        
        # 敏感表名模式
        self._sensitive_table_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                r"users?",  # 用户表
                r"passwords?",  # 密码表
                r"credentials?",  # 凭证表
                r"secrets?",  # 密钥表
                r"tokens?",  # 令牌表
                r"credit_cards?",  # 信用卡表
                r"bank_accounts?",  # 银行账户表
            ]
        ]
        
    def validate_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """验证SQL查询安全性
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Raises:
            SecurityViolationError: 当检测到安全违规时
        """
        # 检查SQL注入
        self._check_sql_injection(query)
        
        # 检查敏感表访问
        self._check_sensitive_tables(query)
        
        # 检查参数
        if params:
            self._check_parameters(params)
            
    def _check_sql_injection(self, query: str) -> None:
        """检查SQL注入
        
        Args:
            query: SQL查询语句
            
        Raises:
            SecurityViolationError: 当检测到SQL注入时
        """
        for pattern in self._sql_injection_patterns:
            if pattern.search(query):
                logger.warning(
                    "SQL injection detected",
                    extra={
                        "query": query,
                        "pattern": pattern.pattern
                    }
                )
                raise SecurityViolationError(
                    "Potential SQL injection detected",
                    details={
                        "query": query,
                        "pattern": pattern.pattern
                    }
                )
                
    def _check_sensitive_tables(self, query: str) -> None:
        """检查敏感表访问
        
        Args:
            query: SQL查询语句
            
        Raises:
            SecurityViolationError: 当检测到未授权的敏感表访问时
        """
        for pattern in self._sensitive_table_patterns:
            if pattern.search(query):
                logger.warning(
                    "Sensitive table access detected",
                    extra={
                        "query": query,
                        "table_pattern": pattern.pattern
                    }
                )
                raise SecurityViolationError(
                    "Unauthorized access to sensitive table",
                    details={
                        "query": query,
                        "table_pattern": pattern.pattern
                    }
                )
                
    def _check_parameters(self, params: Dict[str, Any]) -> None:
        """检查查询参数
        
        Args:
            params: 查询参数
            
        Raises:
            SecurityViolationError: 当检测到不安全的参数时
        """
        for key, value in params.items():
            if isinstance(value, str):
                # 检查字符串参数中的特殊字符
                if any(char in value for char in "';\""):
                    logger.warning(
                        "Suspicious parameter detected",
                        extra={
                            "parameter": key,
                            "value": value
                        }
                    )
                    raise SecurityViolationError(
                        "Suspicious characters in parameter",
                        details={
                            "parameter": key,
                            "value": value
                        }
                    ) 