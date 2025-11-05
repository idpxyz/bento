"""
Avro 到 Pydantic 模型转换器
处理 Avro schema 生成对应的 Pydantic 模型
"""

import json
import os
from typing import Any, Dict, List, Optional, Set, Union

# Avro 类型到 Python 类型的映射
TYPE_MAPPING = {
    'string': 'str',
    'int': 'int',
    'long': 'int',
    'float': 'float',
    'double': 'float',
    'boolean': 'bool',
    'bytes': 'bytes',
    'null': 'None',
}

def get_field_type(field_type: Union[str, Dict, List], imports: Set[str]) -> str:
    """
    解析 Avro 字段类型，返回对应的 Python/Pydantic 类型
    """
    # 如果是简单字符串类型
    if isinstance(field_type, str):
        return TYPE_MAPPING.get(field_type, field_type)
    
    # 如果是 union 类型 (数组形式)
    elif isinstance(field_type, list):
        # 处理 ["null", "string"] 形式的可选类型
        if len(field_type) == 2 and "null" in field_type:
            other_type = next(t for t in field_type if t != "null")
            py_type = get_field_type(other_type, imports)
            return f"Optional[{py_type}]"
        else:
            # 处理一般的联合类型
            imports.add('from typing import Union')
            union_types = [get_field_type(t, imports) for t in field_type]
            return f"Union[{', '.join(union_types)}]"
    
    # 如果是复杂类型 (record, array, map, enum 等)
    elif isinstance(field_type, dict):
        avro_type = field_type.get('type', '')
        
        if avro_type == 'record':
            # 嵌套记录类型
            return field_type.get('name', 'Record')
            
        elif avro_type == 'array':
            # 数组类型
            imports.add('from typing import List')
            items_type = get_field_type(field_type.get('items', 'string'), imports)
            return f"List[{items_type}]"
            
        elif avro_type == 'map':
            # 映射类型
            imports.add('from typing import Dict')
            values_type = get_field_type(field_type.get('values', 'string'), imports)
            return f"Dict[str, {values_type}]"
            
        elif avro_type == 'enum':
            # 枚举类型
            enum_name = field_type.get('name', 'Enum')
            
            # 检查是否可以使用 Literal 类型
            enum_symbols = field_type.get('symbols', [])
            if len(enum_symbols) <= 5 and all(isinstance(s, str) for s in enum_symbols):
                imports.add('from typing import Literal')
                quoted_symbols = [f"'{s}'" for s in enum_symbols]
                return f"Literal[{', '.join(quoted_symbols)}]"
            else:
                imports.add('from enum import Enum')
                return enum_name
            
        elif avro_type == 'fixed':
            # 固定字节类型
            return 'bytes'
            
        elif isinstance(avro_type, str) and avro_type in TYPE_MAPPING:
            # 基本类型
            return TYPE_MAPPING[avro_type]
            
        elif isinstance(avro_type, list) or isinstance(avro_type, dict):
            # 递归处理复杂类型
            return get_field_type(avro_type, imports)
    
    # 默认情况
    return 'Any'

def process_complex_types(schema: Dict, imports: Set[str], processed_types: Set[str]) -> List[str]:
    """
    处理嵌套的复杂类型 (record, enum)，返回对应的 Pydantic 模型定义
    """
    models = []
    
    # 递归处理嵌套类型
    def process_schema(schema_obj: Dict) -> None:
        if isinstance(schema_obj, dict):
            schema_type = schema_obj.get('type', '')
            
            if schema_type == 'record' and 'name' in schema_obj:
                record_name = schema_obj['name']
                
                # 避免重复处理
                if record_name in processed_types:
                    return
                processed_types.add(record_name)
                
                # 处理记录字段
                record_fields = schema_obj.get('fields', [])
                field_lines = []
                
                for field in record_fields:
                    field_name = field['name']
                    field_type = field.get('type', 'string')
                    field_doc = field.get('doc', '')
                    
                    # 先处理嵌套类型
                    process_schema(field_type)
                    
                    # 获取 Python 类型
                    py_type = get_field_type(field_type, imports)
                    
                    # 处理默认值
                    if 'default' in field:
                        field_lines.append(f"    {field_name}: {py_type} = {repr(field['default'])}  # {field_doc}")
                    else:
                        field_lines.append(f"    {field_name}: {py_type}  # {field_doc}")
                
                # 生成记录模型
                class_doc = schema_obj.get('doc', f"{record_name} 模型")
                model_lines = [
                    f"class {record_name}(BaseModel):",
                    f'    """',
                    f'    {class_doc}',
                    f'    """'
                ]
                model_lines.extend(field_lines)
                
                # 添加配置
                model_lines.extend([
                    '',
                    '    class Config:',
                    '        """模型配置"""',
                    "        json_encoders = {",
                    "            datetime: lambda dt: dt.isoformat()",
                    "        }"
                ])
                
                models.append('\n'.join(model_lines))
                
            elif schema_type == 'enum' and 'name' in schema_obj:
                enum_name = schema_obj['name']
                
                # 避免重复处理
                if enum_name in processed_types:
                    return
                processed_types.add(enum_name)
                
                # 获取枚举符号和文档
                enum_doc = schema_obj.get('doc', f"{enum_name} 枚举")
                enum_symbols = schema_obj.get('symbols', [])
                
                # 如果符号数量较少且都是简单字符串，使用 Literal 类型
                # 不需要创建枚举类，因为字段类型中会直接使用 Literal[...]
                if len(enum_symbols) <= 5 and all(isinstance(s, str) for s in enum_symbols):
                    imports.add('from typing import Literal')
                else:
                    # 需要创建枚举类
                    enum_lines = [
                        f"class {enum_name}(str, Enum):",
                        f'    """',
                        f'    {enum_doc}',
                        f'    """'
                    ]
                    
                    for symbol in enum_symbols:
                        enum_lines.append(f"    {symbol} = \"{symbol}\"")
                    
                    models.append('\n'.join(enum_lines))
            
            elif isinstance(schema_type, list):
                for st in schema_type:
                    process_schema(st)
            
            elif isinstance(schema_type, dict):
                process_schema(schema_type)
            
            # 递归处理 array 和 map 中的类型
            if schema_type == 'array' and 'items' in schema_obj:
                process_schema(schema_obj['items'])
            elif schema_type == 'map' and 'values' in schema_obj:
                process_schema(schema_obj['values'])
    
    # 处理主 schema
    process_schema(schema)
    return models

def generate_pydantic_from_avro(avsc_file: str, output_file: str) -> None:
    """
    从 Avro schema 文件生成 Pydantic 模型
    
    Args:
        avsc_file: Avro schema 文件路径
        output_file: 输出的 Python 文件路径
    """
    # 读取 Avro schema
    with open(avsc_file, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    imports = {
        'from datetime import datetime',
        'from typing import Optional, Any',
        'from pydantic import BaseModel, Field'
    }
    
    processed_types = set()
    
    # 生成所有模型
    models = process_complex_types(schema, imports, processed_types)
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('"""')
        f.write(f'\n从 {os.path.basename(avsc_file)} 自动生成的 Pydantic 模型\n')
        f.write('"""\n\n')
        
        # 写入导入
        for import_line in sorted(imports):
            f.write(f"{import_line}\n")
        
        f.write('\n\n')
        
        # 写入模型
        for model in models:
            f.write(f"{model}\n\n")
    
    print(f"✅ 生成 Pydantic 模型: {output_file}")

if __name__ == "__main__":
    # 测试
    avsc_file = "test.avsc"
    output_file = "test_model.py"
    generate_pydantic_from_avro(avsc_file, output_file) 