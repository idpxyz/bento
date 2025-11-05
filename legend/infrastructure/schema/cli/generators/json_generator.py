"""
JSON Schema 到 Pydantic 模型转换器
处理 JSON Schema 生成对应的 Pydantic 模型
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Union

# JSON Schema 类型到 Python 类型的映射
TYPE_MAPPING = {
    'string': 'str',
    'integer': 'int',
    'number': 'float',
    'boolean': 'bool',
    'array': 'List',
    'object': 'Dict',
    'null': 'None',
}

# JSON Schema 格式到 Pydantic 验证器的映射
FORMAT_MAPPING = {
    'date': ('Field(..., json_schema_extra={"format": "date"})', ['from pydantic import Field']),
    'date-time': ('datetime', ['from datetime import datetime']),
    'time': ('time', ['from datetime import time']),
    'email': ('EmailStr', ['from pydantic import EmailStr']),
    'ipv4': ('IPv4Address', ['from ipaddress import IPv4Address']),
    'ipv6': ('IPv6Address', ['from ipaddress import IPv6Address']),
    'uuid': ('UUID', ['from uuid import UUID']),
    'uri': ('AnyUrl', ['from pydantic import AnyUrl']),
}

def snake_to_pascal(name: str) -> str:
    """将 snake_case 转换为 PascalCase"""
    if not name:
        return name
    return ''.join(word.capitalize() for word in name.split('_'))

def get_property_type(
    prop_schema: Dict, 
    imports: Set[str], 
    required: List[str] = None, 
    prop_name: str = None
) -> str:
    """
    解析 JSON Schema 属性，返回对应的 Python/Pydantic 类型
    """
    if required is None:
        required = []
    
    # 处理复合类型 (oneOf, anyOf, allOf)
    if 'oneOf' in prop_schema or 'anyOf' in prop_schema:
        imports.add('from typing import Union')
        subtypes = prop_schema.get('oneOf', prop_schema.get('anyOf', []))
        type_list = [get_property_type(t, imports) for t in subtypes]
        return f"Union[{', '.join(type_list)}]"
    
    # 处理引用类型
    if '$ref' in prop_schema:
        # 解析引用路径，获取类型名
        ref_path = prop_schema['$ref']
        type_name = ref_path.split('/')[-1]
        return type_name

    # 获取基本类型
    prop_type = prop_schema.get('type', 'object')
    
    # 处理数组类型
    if prop_type == 'array':
        imports.add('from typing import List')
        items = prop_schema.get('items', {})
        items_type = get_property_type(items, imports)
        return f"List[{items_type}]"
    
    # 处理对象类型
    elif prop_type == 'object':
        # 如果有明确的 properties，生成嵌套模型
        if 'properties' in prop_schema and prop_name:
            nested_class_name = snake_to_pascal(prop_name)
            return nested_class_name
        else:
            # 通用对象类型
            imports.add('from typing import Dict, Any')
            return "Dict[str, Any]"
    
    # 处理格式化类型
    if 'format' in prop_schema:
        format_type = prop_schema['format']
        if format_type in FORMAT_MAPPING:
            type_str, extra_imports = FORMAT_MAPPING[format_type]
            for imp in extra_imports:
                imports.add(imp)
            return type_str
    
    # 处理枚举类型
    if 'enum' in prop_schema:
        # 添加 Literal 导入
        imports.add('from typing import Literal')
        return f"Literal[{', '.join(repr(v) for v in prop_schema['enum'])}]"
    
    # 处理基本类型
    py_type = TYPE_MAPPING.get(prop_type, 'Any')
    
    # 处理可选性 (非必需字段)
    is_required = prop_name in required if prop_name else False
    if not is_required and py_type != 'Any':
        imports.add('from typing import Optional')
        return f"Optional[{py_type}]"
    
    return py_type

def generate_nested_models(
    schema: Dict, 
    imports: Set[str], 
    processed_models: Set[str]
) -> List[str]:
    """
    生成嵌套模型定义
    """
    models = []
    
    # 递归处理属性对象
    def process_properties(properties: Dict, required: List[str], parent_name: str = "") -> None:
        for prop_name, prop_schema in properties.items():
            # 处理对象类型属性
            if prop_schema.get('type') == 'object' and 'properties' in prop_schema:
                class_name = snake_to_pascal(prop_name)
                
                # 避免重复处理
                qualified_name = f"{parent_name}.{class_name}" if parent_name else class_name
                if qualified_name in processed_models:
                    continue
                processed_models.add(qualified_name)
                
                # 生成嵌套模型
                nested_properties = prop_schema.get('properties', {})
                nested_required = prop_schema.get('required', [])
                
                class_lines = [
                    f"class {class_name}(BaseModel):",
                    f'    """',
                    f'    {prop_schema.get("description", class_name + " 模型")}',
                    f'    """'
                ]
                
                # 递归处理嵌套属性
                process_properties(nested_properties, nested_required, qualified_name)
                
                # 添加字段定义
                for nested_prop, nested_schema in nested_properties.items():
                    field_type = get_property_type(nested_schema, imports, nested_required, nested_prop)
                    description = nested_schema.get('description', '')
                    
                    default_value = None
                    if 'default' in nested_schema:
                        default_value = repr(nested_schema['default'])
                    
                    if nested_prop in nested_required or default_value is not None:
                        if default_value is not None:
                            field_line = f"    {nested_prop}: {field_type} = {default_value}"
                        else:
                            field_line = f"    {nested_prop}: {field_type}"
                    else:
                        field_line = f"    {nested_prop}: {field_type} = None"
                    
                    if description:
                        field_line += f"  # {description}"
                    
                    class_lines.append(field_line)
                
                # 添加配置
                class_lines.extend([
                    '',
                    '    class Config:',
                    '        """模型配置"""',
                    "        json_schema_extra = {",
                    "            'description': " + repr(prop_schema.get('description', '')),
                    "        }"
                ])
                
                models.append('\n'.join(class_lines))
            
            # 处理数组类型，检查 items 是否为对象类型
            elif prop_schema.get('type') == 'array' and 'items' in prop_schema:
                items_schema = prop_schema['items']
                if items_schema.get('type') == 'object' and 'properties' in items_schema:
                    # 为数组项生成模型
                    item_class_name = snake_to_pascal(prop_name[:-1] if prop_name.endswith('s') else prop_name + "Item")
                    process_properties({item_class_name: items_schema}, required, parent_name)
    
    # 处理顶层属性
    if 'properties' in schema:
        process_properties(schema['properties'], schema.get('required', []))
    
    return models

def generate_main_model(schema: Dict, imports: Set[str]) -> str:
    """
    生成主 Pydantic 模型
    """
    # 获取模型名称
    model_name = schema.get('title', 'JSONSchemaModel')
    description = schema.get('description', f"{model_name} 模型")
    
    # 生成模型定义
    lines = [
        f"class {model_name}(BaseModel):",
        f'    """',
        f'    {description}',
        f'    """'
    ]
    
    # 处理属性
    properties = schema.get('properties', {})
    required = schema.get('required', [])
    
    for prop_name, prop_schema in properties.items():
        field_type = get_property_type(prop_schema, imports, required, prop_name)
        
        # 处理描述
        description = prop_schema.get('description', '')
        
        # 处理默认值
        default_value = None
        if 'default' in prop_schema:
            default_value = repr(prop_schema['default'])
        
        # 构建字段定义
        if prop_name in required:
            if default_value is not None:
                field_line = f"    {prop_name}: {field_type} = {default_value}"
            else:
                field_line = f"    {prop_name}: {field_type}"
        else:
            if default_value is not None:
                field_line = f"    {prop_name}: {field_type} = {default_value}"
            else:
                field_line = f"    {prop_name}: {field_type} = None"
        
        if description:
            field_line += f"  # {description}"
        
        lines.append(field_line)
    
    # 添加模型配置
    lines.extend([
        '',
        '    class Config:',
        '        """模型配置"""',
        "        json_schema_extra = {",
        "            'description': " + repr(description),
        "        }"
    ])
    
    # 如果有日期时间类型的字段，添加 datetime 导入和编码器
    has_datetime = any(
        FORMAT_MAPPING.get(prop_schema.get('format', ''), ('', []))[0] == 'datetime'
        for prop_schema in properties.values()
    )
    
    if has_datetime:
        imports.add('from datetime import datetime')
        lines.extend([
            "        json_encoders = {",
            "            datetime: lambda dt: dt.isoformat()",
            "        }"
        ])
    
    return '\n'.join(lines)

def generate_pydantic_from_json(json_schema_file: str, output_file: str) -> None:
    """
    从 JSON Schema 文件生成 Pydantic 模型
    
    Args:
        json_schema_file: JSON Schema 文件路径
        output_file: 输出的 Python 文件路径
    """
    # 读取 JSON Schema
    with open(json_schema_file, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    # 基本导入
    imports = {
        'from pydantic import BaseModel, Field',
        'from typing import Dict, List, Any, Optional'
    }
    
    processed_models = set()
    
    # 生成嵌套模型
    nested_models = generate_nested_models(schema, imports, processed_models)
    
    # 生成主模型
    main_model = generate_main_model(schema, imports)
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('"""')
        f.write(f'\n从 {os.path.basename(json_schema_file)} 自动生成的 Pydantic 模型\n')
        f.write('"""\n\n')
        
        # 写入导入
        for import_line in sorted(imports):
            f.write(f"{import_line}\n")
        
        f.write('\n\n')
        
        # 写入嵌套模型
        for model in nested_models:
            f.write(f"{model}\n\n")
        
        # 写入主模型
        f.write(f"{main_model}\n")
    
    print(f"✅ 生成 Pydantic 模型: {output_file}")

if __name__ == "__main__":
    # 测试
    json_schema_file = "test.json"
    output_file = "test_model.py"
    generate_pydantic_from_json(json_schema_file, output_file) 