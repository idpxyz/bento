"""
Proto 到 Pydantic 模型转换器
处理 Protocol Buffers schema 生成对应的 Pydantic 模型
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Proto 类型到 Python 类型的映射
TYPE_MAPPING = {
    'double': 'float',
    'float': 'float',
    'int32': 'int',
    'int64': 'int',
    'uint32': 'int',
    'uint64': 'int',
    'sint32': 'int',
    'sint64': 'int',
    'fixed32': 'int',
    'fixed64': 'int',
    'sfixed32': 'int',
    'sfixed64': 'int',
    'bool': 'bool',
    'string': 'str',
    'bytes': 'bytes',
}

def parse_proto_file(proto_file: str):
    """解析 .proto 文件，提取包名、消息定义和嵌套消息"""
    with open(proto_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取包名
    package_match = re.search(r'package\s+([^;]+);', content)
    package = package_match.group(1) if package_match else ""
    
    # 处理根级消息定义
    all_messages = []
    all_enums = []
    
    # 首先为每个顶级消息创建一个消息块标记，方便后续分析
    content_blocks = []
    def extract_message_blocks(text, prefix=""):
        """递归提取消息块，包括嵌套消息"""
        # 消息的开始和结束括号位置
        bracket_pairs = []
        open_brackets = []
        
        # 扫描文本，标记所有的括号对
        i = 0
        while i < len(text):
            if text[i] == '{':
                open_brackets.append(i)
            elif text[i] == '}' and open_brackets:
                start = open_brackets.pop()
                bracket_pairs.append((start, i))
            i += 1
        
        # 按照消息定义处理顶级块
        message_pattern = r'message\s+([^\s{]+)\s*{'
        i = 0
        while i < len(text):
            match = re.search(message_pattern, text[i:])
            if not match:
                break
                
            msg_start = i + match.start()
            msg_name = match.group(1)
            
            # 查找与此消息定义对应的括号对
            bracket_end = None
            for start, end in bracket_pairs:
                if start == msg_start + match.end() - 1: # -1 是因为 { 在末尾
                    bracket_end = end
                    break
            
            if bracket_end is not None:
                # 提取完整消息块，包括开始和结束括号
                msg_block = text[msg_start:bracket_end+1]
                full_name = f"{prefix}{msg_name}" if prefix else msg_name
                
                # 添加到块列表
                content_blocks.append({
                    'type': 'message',
                    'name': full_name,
                    'simple_name': msg_name,
                    'content': msg_block,
                    'parent': prefix[:-1] if prefix else None  # 移除末尾的点
                })
                
                # 递归处理嵌套消息
                inner_text = text[msg_start + match.end():bracket_end]
                extract_message_blocks(inner_text, f"{full_name}.")
                
                # 移动到当前消息块之后
                i = bracket_end + 1
            else:
                # 未找到对应的结束括号，移动到下一个字符
                i += 1
        
        # 处理枚举
        enum_pattern = r'enum\s+([^\s{]+)\s*{'
        i = 0
        while i < len(text):
            match = re.search(enum_pattern, text[i:])
            if not match:
                break
                
            enum_start = i + match.start()
            enum_name = match.group(1)
            
            # 查找与此枚举定义对应的括号对
            bracket_end = None
            for start, end in bracket_pairs:
                if start == enum_start + match.end() - 1:
                    bracket_end = end
                    break
            
            if bracket_end is not None:
                # 提取完整枚举块
                enum_block = text[enum_start:bracket_end+1]
                full_name = f"{prefix}{enum_name}" if prefix else enum_name
                
                # 添加到块列表
                content_blocks.append({
                    'type': 'enum',
                    'name': full_name,
                    'simple_name': enum_name,
                    'content': enum_block,
                    'parent': prefix[:-1] if prefix else None  # 移除末尾的点
                })
                
                # 移动到当前枚举块之后
                i = bracket_end + 1
            else:
                # 未找到对应的结束括号，移动到下一个字符
                i += 1
    
    # 提取所有顶级消息和枚举块
    extract_message_blocks(content)
    
    # 处理所有块，解析字段和枚举值
    for block in content_blocks:
        if block['type'] == 'message':
            # 解析消息字段，排除嵌套定义
            fields = parse_message_fields_from_block(block['content'])
            
            # 添加到消息列表
            all_messages.append({
                'name': block['name'],
                'simple_name': block['simple_name'],
                'fields': fields,
                'parent': block['parent']
            })
        elif block['type'] == 'enum':
            # 解析枚举值
            enum_values = parse_enum_values_from_block(block['content'])
            
            # 添加到枚举列表
            all_enums.append({
                'name': block['name'],
                'simple_name': block['simple_name'],
                'values': enum_values,
                'parent': block['parent']
            })
    
    return package, all_messages, all_enums

def parse_message_fields_from_block(message_block):
    """从消息块中解析字段，排除嵌套定义"""
    # 提取消息体（去除消息定义行和嵌套块）
    message_body = re.sub(r'message\s+[^\s{]+\s*{', '', message_block, 1)
    # 移除最后的 }
    message_body = message_body[:-1] if message_body.endswith('}') else message_body
    
    # 移除嵌套 message 和 enum 块
    message_body = re.sub(r'message\s+[^\s{]+\s*{[^}]*}', '', message_body)
    message_body = re.sub(r'enum\s+[^\s{]+\s*{[^}]*}', '', message_body)
    
    # 解析剩余的字段
    return parse_message_fields(message_body)

def parse_enum_values_from_block(enum_block):
    """从枚举块中解析枚举值"""
    # 提取枚举体（去除枚举定义行）
    enum_body = re.sub(r'enum\s+[^\s{]+\s*{', '', enum_block, 1)
    # 移除最后的 }
    enum_body = enum_body[:-1] if enum_body.endswith('}') else enum_body
    
    return parse_enum_values(enum_body)

def generate_pydantic_from_proto(proto_file: str, output_file: str, schema_name: str = None) -> None:
    """
    从 Protocol Buffers 文件生成 Pydantic 模型
    
    Args:
        proto_file: Proto 文件路径
        output_file: 输出文件路径
        schema_name: 可选，指定要生成模型的消息名称
    """
    # 解析 proto 文件
    package, messages, enums = parse_proto_file(proto_file)
    imports = set()
    
    # 基本导入语句
    imports.add("from typing import List, Dict, Optional")
    imports.add("from pydantic import BaseModel, Field")
    imports.add("from enum import Enum")
    
    # 跟踪特殊类型的使用
    uses_timestamp = False
    uses_literal = False
    uses_any = False
    
    # 检查是否使用了 Google Timestamp 类型
    for msg in messages:
        for field in msg['fields']:
            if field['type'] == 'google.protobuf.Timestamp':
                uses_timestamp = True
            
            # 检查字段类型是否需要其他导入
            if field.get('comment') and ('选项:' in field.get('comment') or '选项：' in field.get('comment')):
                uses_literal = True
            
            # 检查是否有泛型字段（需要 Any）
            if field['type'] == 'google.protobuf.Any' or (field['type'].startswith('map<') and 'Any' in field['type']):
                uses_any = True
    
    # 添加必要的导入
    if uses_timestamp:
        imports.add("from datetime import datetime")
    if uses_literal:
        imports.add("from typing import Literal")
    if uses_any:
        imports.add("from typing import Any")
    
    # 过滤要生成的消息
    related_messages = []
    related_enums = []
    main_message = None
    
    if schema_name:
        # 查找主消息
        for msg in messages:
            if msg['name'] == schema_name:
                main_message = msg
                break
                
            # 检查简单名称是否匹配
            if msg['simple_name'] == schema_name and not main_message:
                main_message = msg
        
        if not main_message:
            raise ValueError(f"未找到消息: {schema_name}")
        
        # 收集所有必要的类型
        def collect_dependencies(msg_name, processed=None):
            if processed is None:
                processed = set()
            
            if msg_name in processed:
                return
            
            processed.add(msg_name)
            
            # 查找直接依赖的消息
            # 1. 嵌套在此消息中的类型
            for msg in messages:
                if msg['parent'] == msg_name and msg not in related_messages:
                    related_messages.append(msg)
                    collect_dependencies(msg['name'], processed)
            
            # 2. 嵌套在此消息中的枚举
            for enum in enums:
                if enum['parent'] == msg_name and enum not in related_enums:
                    related_enums.append(enum)
            
            # 3. 此消息引用的其他类型
            current_msg = None
            for msg in messages:
                if msg['name'] == msg_name:
                    current_msg = msg
                    break
            
            if current_msg:
                for field in current_msg['fields']:
                    field_type = field['type']
                    # 跳过基本类型
                    if field_type in TYPE_MAPPING or field_type.startswith('google.protobuf'):
                        continue
                    
                    # 查找引用的消息
                    for dep_msg in messages:
                        # 检查是否为完全匹配的消息名或简单名称
                        if field_type == dep_msg['name'] or field_type == dep_msg['simple_name']:
                            if dep_msg not in related_messages and dep_msg['name'] != msg_name:
                                related_messages.append(dep_msg)
                                collect_dependencies(dep_msg['name'], processed)
                    
                    # 查找引用的枚举
                    for dep_enum in enums:
                        if field_type == dep_enum['name'] or field_type == dep_enum['simple_name']:
                            if dep_enum not in related_enums:
                                related_enums.append(dep_enum)
        
        # 从主消息开始收集依赖
        collect_dependencies(main_message['name'])
        
        # 设置最终要处理的消息和枚举列表
        selected_messages = [main_message] + related_messages
        selected_enums = related_enums
    else:
        # 生成所有消息
        selected_messages = messages
        selected_enums = enums
    
    # 处理所有必要的枚举
    enum_code_blocks = []
    processed_enums = set()
    
    for enum in selected_enums:
        enum_simple_name = enum['simple_name']
        
        # 避免重复定义
        if enum_simple_name in processed_enums:
            continue
        
        processed_enums.add(enum_simple_name)
        
        # 生成枚举代码
        enum_lines = [
            f"class {enum_simple_name}(str, Enum):",
            f'    """枚举类型"""'
        ]
        
        for value in enum['values']:
            comment = f"  # {value['comment']}" if value.get('comment') else ""
            enum_lines.append(f"    {value['name']} = \"{value['name'].lower()}\"{comment}")
        
        enum_code_blocks.append('\n'.join(enum_lines))
    
    # 构建消息依赖关系图
    dependency_graph = {}
    for message in selected_messages:
        message_name = message['simple_name']
        dependencies = set()
        
        # 查找字段依赖
        for field in message['fields']:
            field_type = field['type']
            # 跳过基本类型和特殊类型
            if field_type in TYPE_MAPPING or field_type.startswith('google.protobuf'):
                continue
                
            # 处理数组类型和映射类型
            if field['repeated']:
                # 从 List[] 中提取类型
                inner_type = field_type
            elif field_type.startswith('map<'):
                # 从 map<,> 中提取值类型
                map_types = field_type[4:-1].split(',')
                if len(map_types) == 2:
                    inner_type = map_types[1].strip()
                else:
                    continue
            else:
                inner_type = field_type
                
            # 检查是否引用其他消息
            for other_message in selected_messages:
                other_name = other_message['simple_name']
                if inner_type == other_name or inner_type.endswith('.' + other_name):
                    dependencies.add(other_name)
        
        dependency_graph[message_name] = dependencies
    
    # 使用拓扑排序处理消息定义的顺序
    def topological_sort(graph):
        """拓扑排序算法，确保依赖在前"""
        # 标记: 0=未访问，1=临时标记(用于检测循环)，2=已访问
        marks = {node: 0 for node in graph}
        result = []
        
        def visit(node):
            if marks[node] == 1:
                # 检测到循环依赖，处理方式：仍然添加，但稍后生成代码时需要前向引用
                return
            if marks[node] == 2:
                return
                
            marks[node] = 1  # 临时标记
            
            # 递归访问所有依赖
            for dep in graph.get(node, []):
                if dep in graph:  # 确保依赖存在于图中
                    visit(dep)
            
            marks[node] = 2  # 永久标记
            result.append(node)
        
        # 对每个未访问的节点进行处理
        for node in graph:
            if marks[node] == 0:
                visit(node)
                
        return result
    
    # 获取排序后的消息类型
    sorted_message_names = topological_sort(dependency_graph)
    
    # 将消息对象按拓扑排序重新排列
    sorted_messages = []
    for name in sorted_message_names:
        for msg in selected_messages:
            if msg['simple_name'] == name:
                sorted_messages.append(msg)
                break
    
    # 处理所有必要的消息
    message_code_blocks = []
    processed_messages = set()
    
    for message in sorted_messages:
        message_name = message['simple_name']
        
        # 避免重复定义
        if message_name in processed_messages:
            continue
        
        processed_messages.add(message_name)
        
        # 生成模型文档字符串
        doc_string = f"{message_name} 模型"
        if schema_name and message_name == schema_name:
            doc_string = f"{message_name} 事件模型"
        
        # 生成模型代码
        message_lines = [
            f"class {message_name}(BaseModel):",
            f'    """',
            f"    {doc_string}",
            f'    """'
        ]
        
        # 处理字段
        for field in message['fields']:
            field_name = field['name']
            field_type = field['type']
            python_type = None
            
            # 检查注释中是否有枚举值选项（用于生成 Literal 类型）
            comment = field.get('comment', '')
            literal_values = None
            
            # 在注释中查找 "选项:" 或 "选项：" 后面跟着的枚举值列表
            if '选项:' in comment or '选项：' in comment:
                # 提取选项部分
                options_part = comment.split('选项:')[-1] if '选项:' in comment else comment.split('选项：')[-1]
                
                # 提取引号中的值列表
                import re
                literal_values = re.findall(r"['\"](.*?)['\"]", options_part)
                
                if literal_values:
                    # 标记使用了字面量类型
                    uses_literal = True
                    imports.add("from typing import Literal")
                    
                    # 处理字面量类型
                    quoted_values = [f"'{val}'" for val in literal_values]
                    python_type = f"Literal[{', '.join(quoted_values)}]"
            
            # 如果没有从注释中解析出字面量，则按常规处理类型
            if not literal_values:
                if field_type == 'google.protobuf.Timestamp':
                    python_type = 'datetime'
                elif field_type in TYPE_MAPPING:
                    python_type = TYPE_MAPPING[field_type]
                elif field_type.startswith('map<'):
                    # 处理映射类型
                    map_types = field_type[4:-1].split(',')
                    if len(map_types) == 2:
                        key_type = TYPE_MAPPING.get(map_types[0].strip(), 'str')
                        value_type = TYPE_MAPPING.get(map_types[1].strip(), 'str')
                        python_type = f'Dict[{key_type}, {value_type}]'
                    else:
                        python_type = 'Dict[str, str]'
                else:
                    # 处理消息和枚举引用
                    # 1. 检查是否引用嵌套消息
                    if '.' in field_type:
                        # 使用最后一部分作为类型名
                        python_type = field_type.split('.')[-1]
                    else:
                        # 尝试直接使用类型名
                        python_type = field_type
                        
                        # 验证类型是否存在于消息列表中
                        type_exists = any(msg['simple_name'] == python_type for msg in messages)
                        
                        # 如果没找到，检查枚举列表
                        if not type_exists:
                            type_exists = any(enum['simple_name'] == python_type for enum in enums)
                        
                        # 如果找不到类型，作为字符串处理
                        if not type_exists:
                            python_type = 'str'
            
            # 处理重复字段
            if field['repeated'] and not literal_values:
                python_type = f'List[{python_type}]'
            
            # 处理字段是否必需
            if field.get('required'):
                field_line = f"    {field_name}: {python_type}"
            else:
                field_line = f"    {field_name}: Optional[{python_type}] = None"
            
            # 添加注释
            if comment:
                field_line += f"  # {comment}"
            
            message_lines.append(field_line)
        
        # 添加模型配置 - 使用 Pydantic v2 的 model_config 字典
        message_lines.extend([
            "",
            "    model_config = {",
            '        "json_schema_extra": {"description": "' + doc_string + '"},',
            "        \"json_encoders\": {datetime: lambda dt: dt.isoformat()}",
            "    }"
        ])
        
        message_code_blocks.append('\n'.join(message_lines))
    
    # 生成最终代码
    code_blocks = []
    
    # 文件头
    code_blocks.extend([
        f'"""',
        f"从 {os.path.basename(proto_file)} 自动生成的 Pydantic 模型",
        f'"""',
        "",
        '\n'.join(sorted(imports)),
        ""
    ])
    
    # 先添加所有枚举
    if enum_code_blocks:
        code_blocks.extend(enum_code_blocks)
        code_blocks.append("")
    
    # 再添加所有消息，按依赖顺序
    code_blocks.extend(message_code_blocks)
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(code_blocks))
    
    print(f"[✓] 生成 Pydantic 模型: {output_file}")

def parse_message_fields(message_body):
    """解析消息定义中的字段"""
    fields = []
    
    # 处理每一行
    for line in message_body.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        
        # 提取注释
        comment = ""
        if '//' in line:
            line_parts = line.split('//', 1)
            line = line_parts[0].strip()
            comment = line_parts[1].strip()
        
        # 跳过嵌套消息和枚举定义行
        if line.startswith(('message', 'enum')):
            continue
        
        # 字段格式: modifier? type name = tag [default | deprecated];
        match = re.match(r'(repeated|optional|required)?\s*([^\s]+)\s+([^\s=]+)\s*=\s*(\d+)\s*;?', line)
        if match:
            modifier, field_type, field_name, tag = match.groups()
            fields.append({
                'name': field_name,
                'type': field_type,
                'tag': int(tag),
                'repeated': modifier == 'repeated',
                'required': modifier == 'required',
                'comment': comment
            })
    
    return fields

def parse_enum_values(enum_body):
    """解析枚举定义中的值"""
    values = []
    
    # 处理每一行
    for line in enum_body.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        
        # 提取注释
        comment = ""
        if '//' in line:
            line_parts = line.split('//', 1)
            line = line_parts[0].strip()
            comment = line_parts[1].strip()
        
        # 枚举值格式: NAME = number;
        match = re.match(r'([A-Z0-9_]+)\s*=\s*(\d+)\s*;?', line)
        if match:
            name, number = match.groups()
            values.append({
                'name': name,
                'number': int(number),
                'comment': comment
            })
    
    return values

def proto_type_to_python(proto_type, repeated=False):
    """将 Proto 类型转换为 Python/Pydantic 类型"""
    if proto_type == 'google.protobuf.Timestamp':
        python_type = 'datetime'
    elif proto_type in TYPE_MAPPING:
        python_type = TYPE_MAPPING[proto_type]
    elif proto_type.startswith('map<'):
        # 处理映射类型
        key_value_types = proto_type[4:-1].split(',')
        if len(key_value_types) == 2:
            key_type = TYPE_MAPPING.get(key_value_types[0].strip(), 'str')
            value_type = TYPE_MAPPING.get(key_value_types[1].strip(), 'str')
            python_type = f'Dict[{key_type}, {value_type}]'
        else:
            python_type = 'Dict[str, str]'
    else:
        # 对于其他类型，保持原样（可能是消息引用）
        python_type = proto_type
    
    # 处理重复字段
    if repeated:
        return f'List[{python_type}]'
    
    return python_type

# 测试代码
if __name__ == "__main__":
    proto_file = "test.proto"
    output_file = "test_model.py"
    generate_pydantic_from_proto(proto_file, output_file) 