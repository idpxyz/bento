#!/usr/bin/env python3
"""
Schema 管理工具
提供 Schema 编译、注册、生成文档和 Pydantic 模型等功能
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.dirname(SCRIPT_DIR)

# 定义常量
PROTO_DIR = os.path.join(SCHEMA_DIR, 'proto')
AVRO_DIR = os.path.join(SCHEMA_DIR, 'avro')
JSON_DIR = os.path.join(SCHEMA_DIR, 'json')
GENERATED_DIR = os.path.join(SCHEMA_DIR, 'generated')
MODELS_DIR = os.path.join(GENERATED_DIR, 'models')
DOCS_DIR = os.path.join(SCHEMA_DIR, 'docs')
REGISTRY_FILE = os.path.join(SCHEMA_DIR, 'registry.yml')

# 导入生成器模块
try:
    from .generators import (
        generate_pydantic_from_avro,
        generate_pydantic_from_json,
        generate_pydantic_from_proto,
    )
except ImportError:
    # 如果作为独立脚本运行
    sys.path.append(SCRIPT_DIR)
    from .generators import (
        generate_pydantic_from_avro,
        generate_pydantic_from_json,
        generate_pydantic_from_proto,
    )

# 导入 schema_monitor
try:
    from idp.framework.infrastructure.schema.monitor.schema_monitor import (
        schema_monitor,
    )
except ImportError:
    schema_monitor = None

def load_registry() -> Dict[str, Any]:
    """加载注册表"""
    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"[❌] 加载注册表失败: {e}")
        return {"schemas": [], "options": {}}

def save_registry(registry: Dict[str, Any]) -> None:
    """保存注册表"""
    try:
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(registry, f, default_flow_style=False, sort_keys=False)
        print(f"[✅] 保存注册表成功: {REGISTRY_FILE}")
    except Exception as e:
        print(f"[❌] 保存注册表失败: {e}")

def create_directories() -> None:
    """创建必要的目录"""
    os.makedirs(PROTO_DIR, exist_ok=True)
    os.makedirs(AVRO_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)
    os.makedirs(GENERATED_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, 'schemas'), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, 'guides'), exist_ok=True)

def run_command(cmd: List[str], cwd: str = None) -> bool:
    """运行命令并返回是否成功"""
    try:
        print(f"[🔄] 执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[❌] 命令执行失败: {e}")
        print(e.stderr)
        return False

def build_schemas(args: argparse.Namespace) -> None:
    """编译所有 schema"""
    print("\n[🛠] 开始编译 Schema...")
    create_directories()
    
    registry = load_registry()
    options = registry.get('options', {})
    
    # 处理每个 schema
    for schema in registry.get('schemas', []):
        schema_name = schema['name']
        schema_format = schema['format']
        schema_file = schema['file']
        
        if not all([schema_name, schema_format, schema_file]):
            print(f"[⚠️] 跳过不完整的 schema 定义: {schema}")
            continue
        
        print(f"\n[🔍] 处理 Schema: {schema_name} ({schema_format})")
        
        # 构建文件路径
        schema_path = os.path.join(SCHEMA_DIR, schema_file)
        
        if not os.path.exists(schema_path):
            print(f"[❌] Schema 文件不存在: {schema_path}")
            continue
        
        # 根据格式处理 schema
        if schema_format == 'proto':
            # 编译 .proto 文件
            output_dir = options.get('proto_output_path', 'generated/proto')
            output_path = os.path.join(SCHEMA_DIR, output_dir)
            os.makedirs(output_path, exist_ok=True)
            
            if run_command(['protoc', f'--python_out={output_path}', f'--proto_path={os.path.dirname(schema_path)}', schema_path]):
                print(f"[✅] 编译 {schema_name} 成功")
            else:
                print(f"[❌] 编译 {schema_name} 失败")
        
        elif schema_format == 'avro':
            # 验证 Avro schema
            try:
                with open(schema_path, 'r') as f:
                    avro_schema = json.load(f)
                print(f"[✅] 验证 {schema_name} 成功")
            except Exception as e:
                print(f"[❌] 验证 {schema_name} 失败: {e}")
        
        elif schema_format == 'json':
            # 验证 JSON Schema
            try:
                with open(schema_path, 'r') as f:
                    json_schema = json.load(f)
                print(f"[✅] 验证 {schema_name} 成功")
            except Exception as e:
                print(f"[❌] 验证 {schema_name} 失败: {e}")
        
        else:
            print(f"[⚠️] 不支持的 Schema 格式: {schema_format}")
    
    print("\n[✅] Schema 编译完成")

def generate_models(args: argparse.Namespace) -> None:
    """生成 Pydantic 模型"""
    print("\n[🔄] 开始生成 Pydantic 模型...")
    create_directories()
    
    registry = load_registry()
    options = registry.get('options', {})
    models_dir = options.get('models_output_path', 'generated/models')
    models_output_path = os.path.join(SCHEMA_DIR, models_dir)
    os.makedirs(models_output_path, exist_ok=True)
    
    # 创建 __init__.py
    init_file = os.path.join(models_output_path, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('"""自动生成的 Pydantic 模型\n"""\n\n')
    
    # 处理每个 schema
    success_count = 0
    error_count = 0
    
    for schema in registry.get('schemas', []):
        schema_name = schema.get('name')
        schema_format = schema.get('format')
        schema_file = schema.get('file')
        
        if not all([schema_name, schema_format, schema_file]):
            print(f"[⚠️] 跳过不完整的 schema 定义: {schema}")
            continue
        
        print(f"\n[🔍] 处理 Schema: {schema_name} ({schema_format})")
        
        # 构建文件路径
        schema_path = os.path.join(SCHEMA_DIR, schema_file)
        output_file = os.path.join(models_output_path, f"{schema_name.lower()}.py")
        
        if not os.path.exists(schema_path):
            print(f"[❌] Schema 文件不存在: {schema_path}")
            error_count += 1
            continue
        
        try:
            # 根据格式生成 Pydantic 模型
            if schema_format == 'proto':
                generate_pydantic_from_proto(schema_path, output_file, schema.get('message'))
            elif schema_format == 'avro':
                generate_pydantic_from_avro(schema_path, output_file)
            elif schema_format == 'json':
                generate_pydantic_from_json(schema_path, output_file)
            else:
                print(f"[⚠️] 不支持的 Schema 格式: {schema_format}")
                error_count += 1
                continue
            
            success_count += 1
        except Exception as e:
            print(f"[❌] 生成 {schema_name} 的 Pydantic 模型失败: {e}")
            error_count += 1
    
    # 更新 __init__.py 导出生成的模型
    with open(init_file, 'w') as f:
        f.write('"""自动生成的 Pydantic 模型\n"""\n\n')
        
        for schema in registry.get('schemas', []):
            schema_name = schema.get('name')
            model_file = schema_name.lower()
            f.write(f"from .{model_file} import {schema_name}\n")
        
        f.write("\n__all__ = [\n")
        for schema in registry.get('schemas', []):
            schema_name = schema.get('name')
            f.write(f"    '{schema_name}',\n")
        f.write("]\n")
    
    print(f"\n[✅] Pydantic 模型生成完成: 成功 {success_count}, 失败 {error_count}")

def register_schemas(args: argparse.Namespace) -> None:
    """将 schema 注册到 Schema Registry"""
    print("\n[📡] 开始注册 Schema 到 Registry...")
    
    registry = load_registry()
    options = registry.get('options', {})
    
    # 尝试导入必要的模块
    try:
        import requests
    except ImportError:
        print("[❌] 缺少必要的依赖: requests")
        print("    请安装: pip install requests")
        return
    
    # 获取 Pulsar Admin URL
    pulsar_admin_url = args.url or os.environ.get("PULSAR_ADMIN_URL")
    if not pulsar_admin_url:
        print("[❌] 未指定 Pulsar Admin URL")
        print("    请通过 --url 参数或 PULSAR_ADMIN_URL 环境变量指定")
        return
    
    # 处理每个 schema
    success_count = 0
    error_count = 0
    success_schemas = []
    error_schemas = {}
    start_time = time.time()
    
    for schema in registry.get('schemas', []):
        schema_name = schema.get('name')
        schema_format = schema.get('format')
        schema_file = schema.get('file')
        topic = schema.get('topic')
        
        if not all([schema_name, schema_format, schema_file, topic]):
            print(f"[⚠️] 跳过不完整的 schema 定义: {schema}")
            continue
        
        print(f"\n[🔍] 注册 Schema: {schema_name} 到 {topic}")
        
        # 记录单个 schema 注册开始时间
        schema_start_time = time.time()
        
        # 构建文件路径
        schema_path = os.path.join(SCHEMA_DIR, schema_file)
        
        if not os.path.exists(schema_path):
            error_msg = f"Schema 文件不存在: {schema_path}"
            print(f"[❌] {error_msg}")
            error_count += 1
            error_schemas[schema_name] = error_msg
            
            # 记录日志
            if schema_monitor:
                schema_monitor.log_registration_result(
                    schema_name=schema_name,
                    topic=topic,
                    schema_format=schema_format,
                    schema_type="UNKNOWN",
                    success=False,
                    error_msg=error_msg
                )
            continue
        
        # 读取 schema 内容
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_content = f.read()
        except Exception as e:
            error_msg = f"读取 Schema 文件失败: {e}"
            print(f"[❌] {error_msg}")
            error_count += 1
            error_schemas[schema_name] = error_msg
            
            # 记录日志
            if schema_monitor:
                schema_monitor.log_registration_result(
                    schema_name=schema_name,
                    topic=topic,
                    schema_format=schema_format,
                    schema_type="UNKNOWN",
                    success=False,
                    error_msg=error_msg
                )
            continue
        
        # 解析 topic
        topic_parts = topic.replace("persistent://", "").split("/")
        if len(topic_parts) != 3:
            error_msg = f"无效的 topic 格式: {topic}"
            print(f"[❌] {error_msg}")
            error_count += 1
            error_schemas[schema_name] = error_msg
            
            # 记录日志
            if schema_monitor:
                schema_monitor.log_registration_result(
                    schema_name=schema_name,
                    topic=topic,
                    schema_format=schema_format,
                    schema_type="UNKNOWN",
                    success=False,
                    error_msg=error_msg
                )
            continue
        
        tenant, namespace, topic_name = topic_parts
        
        # 构建请求
        url = f"{pulsar_admin_url}/admin/v2/schemas/{tenant}/{namespace}/{topic_name}/schema"
        headers = {"Content-Type": "application/json"}
        
        # 设置 schema 类型，根据格式
        schema_type_map = {
            'proto': 'PROTOBUF',
            'avro': 'AVRO',
            'json': 'JSON'
        }
        original_schema_type = schema_type_map.get(schema_format, 'JSON')
        
        # 对于 JSON Schema，直接尝试使用 AVRO 类型
        schema_type = "AVRO" if schema_format == 'json' else original_schema_type
        
        # 根据不同的 schema 格式处理内容
        processed_content = schema_content
        properties = {}
        
        try:
            if schema_format == 'proto':
                # 对于 PROTOBUF 类型，转换为 Avro 格式
                try:
                    # 获取消息类型和包名
                    message_name = schema.get('message', schema_name)
                    package_name = schema.get('package', 'events')
                    
                    print(f"  - Message: {message_name}")
                    print(f"  - Package: {package_name}")
                    
                    # 将 Proto 文件转换为 Avro 格式的 JSON 字符串
                    # 这里我们构建一个简化的 Avro 记录，其中包含 Proto 的主要信息
                    avro_schema = {
                        "type": "record",
                        "name": message_name,
                        "namespace": package_name,
                        "fields": []
                    }
                    
                    # 尝试从 proto 文件中提取字段信息
                    import re
                    field_matches = re.finditer(r'(\w+)\s+(\w+)\s*=\s*(\d+)', schema_content)
                    
                    for match in field_matches:
                        field_type, field_name, field_number = match.groups()
                        # 将 proto 类型映射到 Avro 类型
                        avro_type = "string"  # 默认类型
                        if field_type == "int32" or field_type == "int64":
                            avro_type = "int"
                        elif field_type == "float" or field_type == "double":
                            avro_type = "double"
                        elif field_type == "bool":
                            avro_type = "boolean"
                        
                        avro_schema["fields"].append({
                            "name": field_name,
                            "type": avro_type,
                            "doc": f"Field {field_name}"
                        })
                    
                    # 如果没有找到字段，添加一个虚拟字段
                    if not avro_schema["fields"]:
                        avro_schema["fields"].append({
                            "name": "placeholder",
                            "type": "string",
                            "doc": "Placeholder field"
                        })
                    
                    # 转换为 JSON 字符串
                    processed_content = json.dumps(avro_schema)
                    print(f"  - 转换为 Avro 格式: {processed_content[:100]}...")
                    
                    # 添加 Proto 特定属性
                    properties["proto.message"] = message_name
                    properties["proto.package"] = package_name
                    
                except Exception as e:
                    print(f"[❌] 处理 Proto 文件时发生错误: {e}")
                    error_count += 1
                    continue
                
            elif schema_format == 'json':
                try:
                    # 解析 JSON Schema
                    json_obj = json.loads(schema_content)
                    namespace = schema.get('package', 'com.idp.events')
                    
                    # 直接转换为 AVRO 格式
                    avro_schema = json_schema_to_avro(json_obj, schema_name, namespace)
                    
                    # 转换为 JSON 字符串
                    processed_content = json.dumps(avro_schema)
                    print(f"  - 转换为 AVRO 格式: {processed_content[:100]}...")
                    
                    # 添加特定属性
                    properties["__alwaysAllowNull"] = "true"
                    properties["__jsr310ConversionEnabled"] = "true"
                    
                except json.JSONDecodeError as e:
                    print(f"[❌] JSON Schema 格式无效: {e}")
                    error_count += 1
                    continue
                except Exception as e:
                    print(f"[❌] 处理 JSON Schema 时发生错误: {e}")
                    print(f"    详细错误: {str(e)}")
                    error_count += 1
                    continue
            
            elif schema_format == 'avro':
                # 对于 AVRO Schema，确保它是有效的 Avro 格式的 JSON
                try:
                    json_obj = json.loads(schema_content)
                    
                    # 检查是否符合 Avro 规范
                    if not ('type' in json_obj and json_obj.get('type') == 'record' and 'fields' in json_obj):
                        print(f"[⚠️] Avro Schema 不符合规范，尝试修复...")
                        # 尝试将其转换为标准 Avro 格式
                        avro_schema = {
                            "type": "record",
                            "name": schema_name,
                            "namespace": schema.get('package', 'com.idp.events'),
                            "fields": []
                        }
                        
                        # 如果有字段定义，转换它们
                        if 'properties' in json_obj and isinstance(json_obj['properties'], dict):
                            for prop_name, prop_def in json_obj['properties'].items():
                                field = {
                                    "name": prop_name,
                                    "type": convert_json_type_to_avro(prop_def.get('type', 'string')),
                                    "doc": prop_def.get('description', f"Field {prop_name}")
                                }
                                avro_schema["fields"].append(field)
                        
                        json_obj = avro_schema
                        
                    processed_content = json.dumps(json_obj)
                    print(f"  - Avro Schema: {processed_content[:100]}...")
                except json.JSONDecodeError as e:
                    print(f"[❌] AVRO Schema 格式无效: {e}")
                    error_count += 1
                    continue
        except Exception as e:
            error_msg = f"处理 Schema 内容时发生错误: {e}"
            print(f"[❌] {error_msg}")
            error_count += 1
            error_schemas[schema_name] = error_msg
            
            # 记录日志
            if schema_monitor:
                schema_monitor.log_registration_result(
                    schema_name=schema_name,
                    topic=topic,
                    schema_format=schema_format,
                    schema_type=schema_type,
                    success=False,
                    error_msg=error_msg
                )
            continue
            
        # 构建请求数据
        payload = {
            "type": schema_type,
            "schema": processed_content,
            "properties": properties
        }
        
        # 发送请求
        try:
            print(f"  - 提交 {schema_format} 格式的 Schema (使用 {schema_type} 类型)...")
            
            # 调试信息
            print(f"  - Schema 内容预览: {processed_content[:200]}...")
            print(f"  - payload 类型: {type(payload)}, schema 字段类型: {type(payload['schema'])}")
            
            response = requests.post(url, json=payload, headers=headers)
            
            # 如果失败，尝试回退到原始类型
            if response.status_code in (409, 422) and schema_format == 'json' and schema_type != original_schema_type:
                print(f"  - AVRO 类型注册失败，尝试回退到 {original_schema_type} 类型...")
                
                # 解析 JSON Schema
                json_obj = json.loads(schema_content)
                
                # 确保它是一个有效的 JSON Schema
                if '$schema' not in json_obj:
                    json_obj['$schema'] = "http://json-schema.org/draft-07/schema#"
                
                if 'type' not in json_obj or json_obj['type'] != 'object':
                    json_obj['type'] = 'object'
                
                if 'properties' not in json_obj:
                    json_obj['properties'] = {}
                
                # 序列化回 JSON 字符串
                processed_content = json.dumps(json_obj)
                print(f"  - 原始 JSON Schema: {processed_content[:100]}...")
                
                # 更新 payload 并重新发送请求
                payload["type"] = original_schema_type
                payload["schema"] = processed_content
                
                print(f"  - 重新提交为 {original_schema_type} 类型...")
                response = requests.post(url, json=payload, headers=headers)
            
            # 如果还是失败，使用极简 AVRO 模式再试一次
            if response.status_code in (409, 422) and schema_format == 'json':
                print("  - 尝试使用极简 AVRO 模式...")
                
                # 创建极简 AVRO 模式
                simple_avro = {
                    "type": "record",
                    "name": schema_name,
                    "namespace": schema.get('package', 'com.idp.events'),
                    "fields": [
                        {
                            "name": "data",
                            "type": "string",
                            "doc": "JSON 数据"
                        }
                    ]
                }
                
                # 更新 payload 并重新发送请求
                payload["type"] = "AVRO"
                payload["schema"] = json.dumps(simple_avro)
                
                print(f"  - 使用极简 AVRO 模式重试...")
                response = requests.post(url, json=payload, headers=headers)
            
            # 如果 AVRO 或 PROTOBUF 类型失败，可能需要删除重新注册
            # 这里简单提示用户，后续可以扩展为自动删除重注册
            if response.status_code == 409 and schema_format in ('proto', 'avro'):
                print(f"  - 已存在不同类型的 Schema，如需更改类型，请先删除现有 Schema...")
            
            # 调试信息
            if response.status_code not in (200, 204):
                print(f"  - 请求 URL: {url}")
                print(f"  - 请求头: {headers}")
                print(f"  - 请求正文类型: {type(payload)}")
                print(f"  - Schema 类型: {payload['type']}")
                print(f"  - 属性: {properties}")
                print(f"  - 响应状态码: {response.status_code}")
                print(f"  - 响应内容: {response.text}")
                
            if response.status_code in (200, 204):
                # 计算持续时间
                schema_duration_ms = (time.time() - schema_start_time) * 1000
                
                print(f"[✅] 注册 {schema_name} 成功")
                success_count += 1
                success_schemas.append(schema_name)
                
                # 记录日志
                if schema_monitor:
                    schema_monitor.log_registration_result(
                        schema_name=schema_name,
                        topic=topic,
                        schema_format=schema_format,
                        schema_type=payload["type"],
                        success=True,
                        status_code=response.status_code,
                        duration_ms=schema_duration_ms
                    )
            else:
                # 计算持续时间
                schema_duration_ms = (time.time() - schema_start_time) * 1000
                
                error_detail = response.text[:200] + "..." if len(response.text) > 200 else response.text
                error_msg = f"HTTP {response.status_code}: {error_detail}"
                print(f"[❌] 注册 {schema_name} 失败: HTTP {response.status_code}")
                print(f"    错误详情: {error_detail}")
                error_count += 1
                error_schemas[schema_name] = error_msg
                
                # 记录日志
                if schema_monitor:
                    schema_monitor.log_registration_result(
                        schema_name=schema_name,
                        topic=topic,
                        schema_format=schema_format,
                        schema_type=payload["type"],
                        success=False,
                        error_msg=error_detail,
                        status_code=response.status_code,
                        duration_ms=schema_duration_ms
                    )
        except Exception as e:
            error_msg = f"注册 {schema_name} 失败: {e}"
            print(f"[❌] {error_msg}")
            error_count += 1
            error_schemas[schema_name] = str(e)
            
            # 记录日志
            if schema_monitor:
                schema_monitor.log_registration_result(
                    schema_name=schema_name,
                    topic=topic,
                    schema_format=schema_format,
                    schema_type=schema_type,
                    success=False,
                    error_msg=str(e)
                )
    
    # 计算总持续时间
    total_duration_ms = (time.time() - start_time) * 1000
    
    print(f"\n[📊] Schema 注册结果: 成功 {success_count}, 失败 {error_count}")
    
    # 记录注册汇总日志
    if schema_monitor:
        schema_monitor.log_registration_summary(
            success_count=success_count,
            error_count=error_count,
            success_schemas=success_schemas,
            error_schemas=error_schemas,
            total_duration_ms=total_duration_ms
        )
        
        # 收集并记录指标
        schema_monitor.collect_metrics(registry, success_schemas, error_schemas)

def generate_schema_doc(schema: Dict) -> str:
    """
    为 Schema 生成详细文档内容
    
    Args:
        schema: Schema 定义
        
    Returns:
        str: Markdown 格式的文档内容
    """
    schema_name = schema.get('name', 'Unknown')
    schema_desc = schema.get('description', 'No description')
    schema_format = schema.get('format', 'Unknown')
    schema_topic = schema.get('topic', '')
    schema_version = schema.get('version', 1)
    
    content = [
        f"# {schema_name}",
        "",
        f"*{schema_desc}*",
        "",
        f"## 基本信息",
        "",
        f"- **格式**: {schema_format.upper()}",
        f"- **主题**: `{schema_topic}`",
        f"- **版本**: {schema_version}",
        ""
    ]
    
    # 添加模式定义
    content.extend([
        "## Schema 定义",
        ""
    ])
    
    schema_definition = schema.get('schema')
    if not schema_definition and 'file' in schema:
        try:
            # 尝试从文件加载 schema
            file_path = os.path.join(SCHEMA_DIR, schema['file'])
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    if schema_format == 'json':
                        import json
                        schema_definition = json.load(f)
                    elif schema_format == 'avro':
                        import json
                        schema_definition = json.load(f)
                    elif schema_format == 'proto':
                        schema_definition = {'content': f.read()}
        except Exception as e:
            print(f"[⚠️] 加载 Schema 文件失败: {e}")
    
    if schema_definition:
        if schema_format == 'json' or schema_format == 'avro':
            content.extend([
                "```json",
                json.dumps(schema_definition, indent=2, ensure_ascii=False),
                "```",
                ""
            ])
        elif schema_format == 'proto':
            content.extend([
                "```protobuf",
                schema_definition.get('content', '// Proto 定义不可用'),
                "```",
                ""
            ])
    else:
        content.append("*Schema 定义不可用*\n")
    
    # 添加使用示例
    content.extend([
        "## 使用示例",
        "",
        "### 发布事件",
        "",
        "```python",
        f"from idp.framework.infrastructure.schema import load_schema",
        f"from idp.framework.infrastructure.messaging import EventBus",
        "",
        f"# 获取 Schema 并使用它创建事件",
        f"schema = load_schema('{schema_name}')",
        f"topic = schema.get('topic')",
        "",
        f"# 创建事件数据",
        f"event_data = {{",
        f"    # 填充事件数据",
        f"}}",
        "",
        f"# 发布事件",
        f"await event_bus.publish(topic, event_data)",
        "```",
        "",
        "### 订阅事件",
        "",
        "```python",
        f"from idp.framework.infrastructure.messaging import EventBus",
        "",
        f"# 订阅事件",
        f"@event_bus.subscribe('{schema_topic}')",
        f"async def handle_{schema_name.lower()}(data):",
        f"    # 处理事件数据",
        f"    print(f'收到 {schema_name} 事件: {{data}}')",
        "```",
        ""
    ])
    
    return '\n'.join(content)

def generate_html_from_md(md_path: str, html_path: str, title: str = None) -> None:
    """
    将单个 Markdown 文件转换为 HTML 文件
    
    Args:
        md_path: Markdown 文件路径
        html_path: 输出的 HTML 文件路径
        title: 页面标题，默认从 Markdown 中提取
    """
    try:
        import markdown
        from bs4 import BeautifulSoup

        # 读取 Markdown 文件
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # 转换 Markdown 为 HTML
        html_content = markdown.markdown(
            md_content, 
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        
        # 如果未指定标题，从 Markdown 内容中提取
        if title is None:
            soup = BeautifulSoup(html_content, 'html.parser')
            h1 = soup.find('h1')
            title = h1.text if h1 else os.path.basename(md_path).replace('.md', '')
        
        # HTML 模板
        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - IDP Schema Center</title>
    <style>
        :root {{
            --primary-color: #4285f4;
            --text-color: #333;
            --bg-color: #fff;
            --header-bg: #4285f4;
            --sidebar-bg: #f5f5f5;
            --border-color: #e0e0e0;
            --code-bg: rgba(27, 31, 35, 0.05);
            --pre-bg: #f6f8fa;
            --sidebar-width: 280px;
            --toc-width: 240px;
            --header-height: 60px;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }}
        
        [data-theme="dark"] {{
            --primary-color: #64b5f6;
            --text-color: #e0e0e0;
            --bg-color: #121212;
            --header-bg: #1a1a1a;
            --sidebar-bg: #1e1e1e;
            --border-color: #333;
            --code-bg: rgba(240, 246, 252, 0.15);
            --pre-bg: #282c34;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: var(--font-sans);
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
            transition: background-color 0.3s ease;
        }}
        
        header {{
            height: var(--header-height);
            background-color: var(--header-bg);
            color: white;
            display: flex;
            align-items: center;
            padding: 0 20px;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: background-color 0.3s ease;
        }}
        
        .logo {{
            font-weight: bold;
            font-size: 1.25rem;
            margin-right: 20px;
        }}
        
        .main-container {{
            display: flex;
            height: calc(100vh - var(--header-height));
            margin-top: var(--header-height);
        }}
        
        .sidebar {{
            width: var(--sidebar-width);
            background-color: var(--sidebar-bg);
            overflow-y: auto;
            border-right: 1px solid var(--border-color);
            padding: 20px;
            flex-shrink: 0;
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }}
        
        .content-container {{
            flex: 1;
            overflow: hidden;
            display: flex;
        }}
        
        .content {{
            flex-grow: 1;
            width: 0;
            overflow-y: auto;
            padding: 40px;
            margin: 0 auto;
        }}
        
        .toc {{
            width: var(--toc-width);
            padding: 20px;
            border-left: 1px solid var(--border-color);
            flex-shrink: 0;
            overflow-y: auto;
            transition: border-color 0.3s ease;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 600;
            line-height: 1.25;
        }}
        
        h1 {{
            font-size: 2em;
            padding-bottom: 0.3em;
            border-bottom: 1px solid var(--border-color);
            margin-top: 0;
            transition: border-color 0.3s ease;
        }}
        
        h2 {{
            font-size: 1.5em;
            padding-bottom: 0.3em;
            border-bottom: 1px solid var(--border-color);
            transition: border-color 0.3s ease;
        }}
        
        h3 {{
            font-size: 1.25em;
        }}
        
        p, ul, ol {{
            margin-bottom: 16px;
        }}
        
        a {{
            color: var(--primary-color);
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        code {{
            font-family: var(--font-mono);
            background-color: var(--code-bg);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 85%;
            transition: background-color 0.3s ease;
        }}
        
        pre {{
            background-color: var(--pre-bg);
            border-radius: 3px;
            padding: 16px;
            overflow: auto;
            margin-bottom: 16px;
            transition: background-color 0.3s ease;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            margin: 0;
            font-size: 90%;
            word-break: normal;
            white-space: pre;
            overflow: visible;
            line-height: inherit;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }}
        
        table th, table td {{
            padding: 6px 13px;
            border: 1px solid var(--border-color);
            transition: border-color 0.3s ease;
        }}
        
        table th {{
            background-color: var(--pre-bg);
            font-weight: 600;
            transition: background-color 0.3s ease;
        }}
        
        table tr:nth-child(2n) {{
            background-color: var(--pre-bg);
            transition: background-color 0.3s ease;
        }}
        
        img {{
            max-width: 100%;
        }}
        
        blockquote {{
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid var(--border-color);
            margin-bottom: 16px;
            transition: border-color 0.3s ease;
        }}
        
        hr {{
            height: 0.25em;
            padding: 0;
            margin: 24px 0;
            background-color: var(--border-color);
            border: 0;
            transition: background-color 0.3s ease;
        }}
        
        .nav-list {{
            list-style: none;
        }}
        
        .nav-list li {{
            margin-bottom: 8px;
        }}
        
        .nav-list li a {{
            display: block;
            padding: 4px 0;
        }}
        
        .nav-category {{
            margin-top: 16px;
            font-weight: bold;
            color: var(--text-color);
            transition: color 0.3s ease;
        }}
        
        .search-box {{
            margin-bottom: 20px;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 8px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background-color: var(--bg-color);
            color: var(--text-color);
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }}
        
        @media (max-width: 1200px) {{
            .toc {{
                display: none;
            }}
        }}
        
        @media (max-width: 900px) {{
            .sidebar {{
                width: 240px;
            }}
        }}
        
        @media (max-width: 768px) {{
            .sidebar {{
                display: none;
            }}
        }}
        
        /* 主题切换 */
        .theme-toggle {{
            cursor: pointer;
            margin-left: auto;
            padding: 8px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.3s ease;
        }}
        
        .theme-toggle:hover {{
            background-color: rgba(255, 255, 255, 0.1);
        }}
        
        /* 链接样式优化 */
        .content a:not(:hover) {{
            text-decoration: none;
            border-bottom: 1px solid rgba(66, 133, 244, 0.3);
        }}
        
        .content a:hover {{
            border-bottom-color: var(--primary-color);
        }}
        
        /* 代码高亮 */
        .codehilite {{
            background: var(--pre-bg);
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }}
        
        .codehilite pre {{
            padding: 1em;
            margin: 0;
            overflow: auto;
        }}

        /* Center - 居中 */
        div[align="center"] {{
            text-align: center;
            margin: 1.5em 0;
        }}
        
        /* 目录项目样式 */
        .toc ul {{
            list-style: none;
            padding-left: 1em;
        }}
        
        .toc > ul {{
            padding-left: 0;
        }}
        
        .toc li {{
            margin-bottom: 0.5em;
        }}
        
        .toc-title {{
            font-weight: bold;
            margin-bottom: 1em;
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo">IDP Schema Center</div>
        <nav>
            <a href="index.html" style="color: white; margin-right: 15px;">首页</a>
            <a href="usage.html" style="color: white; margin-right: 15px;">使用指南</a>
            <a href="proto.html" style="color: white; margin-right: 15px;">Proto</a>
            <a href="avro.html" style="color: white; margin-right: 15px;">Avro</a>
            <a href="json.html" style="color: white; margin-right: 15px;">JSON</a>
        </nav>
        <div class="theme-toggle" id="theme-toggle">🔆</div>
    </header>
    
    <div class="main-container">
        <aside class="sidebar">
            <div class="search-box">
                <input type="text" placeholder="搜索..." id="search-input">
            </div>
            
            <div class="nav-category">文档</div>
            <ul class="nav-list">
                <li><a href="index.html">首页</a></li>
                <li><a href="usage.html">使用指南</a></li>
                <li><a href="proto.html">Proto 事件</a></li>
                <li><a href="avro.html">Avro 事件</a></li>
                <li><a href="json.html">JSON 事件</a></li>
            </ul>
            
            <div class="nav-category">指南</div>
            <ul class="nav-list guides-list">
                {guides_links}
            </ul>
            
            <div class="nav-category">Schema 列表</div>
            <ul class="nav-list schema-list">
                {schema_links}
            </ul>
        </aside>
        
        <div class="content-container">
            <main class="content">
                {content}
            </main>
            
            <div class="toc">
                <div class="toc-title">目录</div>
                <div id="toc-content"></div>
            </div>
        </div>
    </div>
    
    <script>
    // 主题切换功能
    (function() {{
        const toggleButton = document.getElementById('theme-toggle');
        const body = document.documentElement;
        
        // 检查本地存储的主题偏好
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {{
            body.setAttribute('data-theme', savedTheme);
            toggleButton.textContent = savedTheme === 'dark' ? '🌙' : '🔆';
        }}
        
        // 添加点击事件
        toggleButton.addEventListener('click', function() {{
            const currentTheme = body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // 更新图标
            toggleButton.textContent = newTheme === 'dark' ? '🌙' : '🔆';
        }});
    }})();
    
    // 生成目录
    (function() {{
        const content = document.querySelector('.content');
        const headings = content.querySelectorAll('h2, h3, h4');
        const tocContent = document.getElementById('toc-content');
        
        if (headings.length === 0) {{
            document.querySelector('.toc').style.display = 'none';
            return;
        }}
        
        const toc = document.createElement('ul');
        tocContent.appendChild(toc);
        
        headings.forEach((heading, index) => {{
            // 为每个标题添加 ID
            if (!heading.id) {{
                heading.id = `heading-${{index}}`;
            }}
            
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `#${{heading.id}}`;
            a.textContent = heading.textContent;
            
            if (heading.tagName === 'H3') {{
                li.style.marginLeft = '1em';
            }} else if (heading.tagName === 'H4') {{
                li.style.marginLeft = '2em';
            }}
            
            li.appendChild(a);
            toc.appendChild(li);
        }});
    }})();
    
    // 搜索功能
    (function() {{
        const searchInput = document.getElementById('search-input');
        
        if (searchInput) {{
            const schemaItems = document.querySelectorAll('.schema-list li');
            
            searchInput.addEventListener('input', function() {{
                const searchTerm = this.value.toLowerCase();
                
                schemaItems.forEach(item => {{
                    const text = item.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {{
                        item.style.display = 'block';
                    }} else {{
                        item.style.display = 'none';
                    }}
                }});
            }});
        }}
    }})();
    </script>
</body>
</html>
"""
        
        # 准备所有 schema 链接
        registry = load_registry()
        schema_links = []
        for schema in sorted(registry.get('schemas', []), key=lambda s: s.get('name', '')):
            schema_name = schema.get('name', '')
            if schema_name:
                html_file = f"{schema_name.lower()}.html"
                schema_links.append(f'<li><a href="{html_file}">{schema_name}</a></li>')
        
        schema_links_html = '\n                    '.join(schema_links)
        
        # 准备指南链接
        guides_links = []
        guides_dir = os.path.join(SCHEMA_DIR, 'docs', 'guides')
        if os.path.exists(guides_dir):
            for md_file in os.listdir(guides_dir):
                if md_file.endswith('.md'):
                    guide_name = md_file[:-3]  # 移除 .md 扩展名
                    # 从文件名生成显示文本
                    display_name = guide_name.replace('_', ' ').title()
                    if guide_name == 'usage':
                        display_name = '使用指南'
                    elif guide_name == 'event_bus_integration':
                        display_name = 'Event Bus 集成'
                    
                    html_file = f"{guide_name}.html"
                    guides_links.append(f'<li><a href="{html_file}">{display_name}</a></li>')
        
        if not guides_links:
            guides_links.append('<li><a href="usage.html">使用指南</a></li>')
        
        guides_links_html = '\n                    '.join(guides_links)
        
        # 应用模板
        full_html = html_template.format(
            title=title, 
            content=html_content,
            schema_links=schema_links_html,
            guides_links=guides_links_html
        )
        
        # 将相对链接从 .md 转换为 .html
        soup = BeautifulSoup(full_html, 'html.parser')
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            if href.endswith('.md'):
                a_tag['href'] = href.replace('.md', '.html')
        
        # 写入 HTML 文件
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        print(f"[✅] 生成 HTML 文档: {html_path}")
        
    except ImportError as e:
        print(f"[⚠️] 导入错误: {e}")
        print("    请安装所需依赖: pip install markdown beautifulsoup4")
    except Exception as e:
        print(f"[❌] 生成 HTML 时出错: {e}")

def generate_docs(args: argparse.Namespace) -> None:
    """生成 Schema 文档"""
    print("\n[📝] 开始生成 Schema 文档...")
    create_directories()
    
    registry = load_registry()
    options = registry.get('options', {})
    docs_dir = options.get('docs_output_path', 'docs/schemas')
    docs_output_path = os.path.join(SCHEMA_DIR, docs_dir)
    os.makedirs(docs_output_path, exist_ok=True)
    
    # 文档 URL 基础路径
    base_url = options.get('docs_base_url', '')
    
    # 按格式分组
    proto_schemas = []
    avro_schemas = []
    json_schemas = []
    
    # 更新注册表中的文档链接
    updated_schemas = []
    update_registry = False
    
    for schema in registry.get('schemas', []):
        schema_format = schema.get('format')
        schema_name = schema.get('name')
        
        if schema_format == 'proto':
            proto_schemas.append(schema)
        elif schema_format == 'avro':
            avro_schemas.append(schema)
        elif schema_format == 'json':
            json_schemas.append(schema)
        
        # 为每个 schema 添加文档链接
        doc_url = f"{base_url}{schema_name.lower()}.html"
        
        # 创建更新的 schema 条目
        updated_schema = schema.copy()
        if 'doc_url' not in schema or schema['doc_url'] != doc_url:
            updated_schema['doc_url'] = doc_url
            update_registry = True
        
        updated_schemas.append(updated_schema)
    
    # 如果有更新，保存注册表
    if update_registry:
        registry['schemas'] = updated_schemas
        save_registry(registry)
        print("[✅] 已更新注册表中的文档链接")
    
    # 生成格式特定文档
    def generate_format_doc(schemas, format_name, output_file):
        """生成特定格式的文档"""
        content = [
            f"# {format_name} 事件",
            "",
            f"本页列出了所有使用 {format_name} 格式定义的事件。",
            ""
        ]
        
        for schema in schemas:
            schema_name = schema.get('name')
            schema_desc = schema.get('description', 'No description')
            schema_topic = schema.get('topic', '')
            doc_url = schema.get('doc_url', f"{schema_name.lower()}.html")
            
            content.extend([
                f"## {schema_name}",
                "",
                f"{schema_desc}",
                "",
                f"- **Topic**: `{schema_topic}`",
                f"- [详细信息]({schema_name.lower()}.md) | [HTML 文档]({doc_url})",
                ""
            ])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
    
    # 生成索引文档
    index_content = [
        "# Schema 文档索引",
        "",
        "## 事件类型",
        "",
        "- [Protocol Buffers 事件](proto.md)",
        "- [Avro 事件](avro.md)",
        "- [JSON Schema 事件](json.md)",
        "",
        "## 所有事件列表",
        "",
        "| 名称 | 格式 | 描述 | 文档 |",
        "|------|------|------|------|"
    ]
    
    for schema in registry.get('schemas', []):
        schema_name = schema.get('name')
        schema_format = schema.get('format', '').upper()
        schema_desc = schema.get('description', '')
        doc_url = schema.get('doc_url', f"{schema_name.lower()}.html")
        
        index_content.append(f"| {schema_name} | {schema_format} | {schema_desc} | [查看文档]({doc_url}) |")
    
    index_file = os.path.join(docs_output_path, "index.md")
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(index_content))
    
    print(f"[✅] 生成文档索引: {index_file}")
    
    # 生成各格式总览文档
    if proto_schemas:
        generate_format_doc(proto_schemas, "Protocol Buffers", os.path.join(docs_output_path, "proto.md"))
    if avro_schemas:
        generate_format_doc(avro_schemas, "Avro", os.path.join(docs_output_path, "avro.md"))
    if json_schemas:
        generate_format_doc(json_schemas, "JSON", os.path.join(docs_output_path, "json.md"))
    
    # 生成每个 schema 的详细文档
    for schema in registry.get('schemas', []):
        schema_name = schema.get('name')
        if not schema_name:
            continue
        
        doc_content = generate_schema_doc(schema)
        doc_file = os.path.join(docs_output_path, f"{schema_name.lower()}.md")
        
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"[✅] 生成 {schema_name} 文档")
    
    # 生成 HTML 文档
    html_output_path = os.path.join(SCHEMA_DIR, 'generated', 'html')
    os.makedirs(html_output_path, exist_ok=True)
    
    try:
        # 处理主文档
        generate_html_from_md(os.path.join(docs_output_path, "index.md"), os.path.join(html_output_path, "index.html"), "Schema 文档索引")
        
        # 生成各格式总览文档
        if proto_schemas:
            generate_html_from_md(os.path.join(docs_output_path, "proto.md"), os.path.join(html_output_path, "proto.html"), "Protocol Buffers 事件")
        if avro_schemas:
            generate_html_from_md(os.path.join(docs_output_path, "avro.md"), os.path.join(html_output_path, "avro.html"), "Avro 事件")
        if json_schemas:
            generate_html_from_md(os.path.join(docs_output_path, "json.md"), os.path.join(html_output_path, "json.html"), "JSON Schema 事件")
        
        # 生成每个 schema 的详细文档
        for schema in registry.get('schemas', []):
            schema_name = schema.get('name')
            if not schema_name:
                continue
            
            doc_file = os.path.join(docs_output_path, f"{schema_name.lower()}.md")
            generate_html_from_md(doc_file, os.path.join(html_output_path, f"{schema_name.lower()}.html"), schema_name)
            
            print(f"[✅] 生成 {schema_name} HTML 文档")
            
        # 转换 guides 目录中的所有 Markdown 文件
        guides_dir = os.path.join(SCHEMA_DIR, 'docs', 'guides')
        if os.path.exists(guides_dir):
            print("\n[📚] 处理指南文档...")
            for md_file in os.listdir(guides_dir):
                if md_file.endswith('.md'):
                    guide_name = md_file[:-3]  # 移除 .md 扩展名
                    md_path = os.path.join(guides_dir, md_file)
                    html_path = os.path.join(html_output_path, f"{guide_name}.html")
                    
                    # 从文件名生成标题
                    title = guide_name.replace('_', ' ').title()
                    if guide_name == 'usage':
                        title = 'Schema Center 使用指南'
                    
                    generate_html_from_md(md_path, html_path, title)
                    print(f"[✅] 生成指南: {guide_name}")
        
        print(f"\n[✅] HTML 文档生成完成，输出目录: {html_output_path}")
        
    except ImportError:
        print("[⚠️] 未安装 markdown 或 bs4 模块，跳过 HTML 文档生成")
        print("    请安装所需依赖: pip install markdown beautifulsoup4")
    
    print(f"\n[✅] 文档生成完成，输出目录: {docs_output_path}")
    print(f"    使用 'make serve-docs' 启动文档服务器查看")
    
    # 提示如何打开 HTML 文档
    if os.path.exists(html_output_path):
        index_html = os.path.join(html_output_path, 'index.html')
        if os.path.exists(index_html):
            print(f"    HTML 文档: {index_html}")
            print(f"    直接在浏览器中打开上述文件即可查看文档")

def create_schema(args: argparse.Namespace) -> None:
    """创建新的 schema"""
    schema_name = args.name
    schema_format = args.format
    schema_desc = args.desc or f"{schema_name} 事件"
    
    if not schema_name:
        print("[❌] 未提供 schema 名称")
        return
    
    if schema_format not in ('proto', 'avro', 'json'):
        print(f"[❌] 不支持的 schema 格式: {schema_format}")
        return
    
    print(f"\n[🆕] 创建新 Schema: {schema_name} ({schema_format})")
    
    # 加载注册表
    registry = load_registry()
    
    # 检查是否已存在同名 schema
    for schema in registry.get('schemas', []):
        if schema.get('name') == schema_name:
            print(f"[❌] Schema {schema_name} 已存在")
            return
    
    # 创建必要的目录
    create_directories()
    
    # 确定文件名和路径
    file_extensions = {'proto': '.proto', 'avro': '.avsc', 'json': '.json'}
    file_ext = file_extensions.get(schema_format)
    file_name = f"{schema_name.lower()}{file_ext}"
    
    format_dirs = {'proto': PROTO_DIR, 'avro': AVRO_DIR, 'json': JSON_DIR}
    output_dir = format_dirs.get(schema_format)
    
    file_path = os.path.join(output_dir, file_name)
    file_rel_path = os.path.join(schema_format, file_name)
    
    # 创建 schema 文件
    if schema_format == 'proto':
        content = f"""syntax = "proto3";

package events;

import "google/protobuf/timestamp.proto";

// {schema_desc}
message {schema_name} {{
    string id = 1;                             // 唯一ID
    string data = 2;                           // 示例数据字段
    google.protobuf.Timestamp created_at = 3;  // 创建时间
}}
"""
    elif schema_format == 'avro':
        content = f"""{{
  "type": "record",
  "name": "{schema_name}",
  "namespace": "com.idp.events",
  "doc": "{schema_desc}",
  "fields": [
    {{
      "name": "id",
      "type": "string",
      "doc": "唯一ID"
    }},
    {{
      "name": "data",
      "type": "string",
      "doc": "示例数据字段"
    }},
    {{
      "name": "created_at",
      "type": {{
        "type": "long",
        "logicalType": "timestamp-millis"
      }},
      "doc": "创建时间"
    }}
  ]
}}
"""
    else:  # json
        content = f"""{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "{schema_name}",
  "description": "{schema_desc}",
  "type": "object",
  "required": [
    "id",
    "data",
    "created_at"
  ],
  "properties": {{
    "id": {{
      "type": "string",
      "description": "唯一ID"
    }},
    "data": {{
      "type": "string",
      "description": "示例数据字段"
    }},
    "created_at": {{
      "type": "string",
      "format": "date-time",
      "description": "创建时间"
    }}
  }}
}}
"""
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[✅] 创建 Schema 文件: {file_path}")
    
    # 构建 topic 名称
    topic_name = f"{schema_name.lower().replace('_', '.')}"
    default_namespace = registry.get('options', {}).get('default_namespace', 'public/default')
    topic = f"persistent://{default_namespace}/{topic_name}"
    
    # 更新注册表
    schema_entry = {
        "name": schema_name,
        "format": schema_format,
        "topic": topic,
        "file": file_rel_path,
        "description": schema_desc
    }
    
    # 对于 proto 格式，添加额外信息
    if schema_format == 'proto':
        schema_entry["package"] = "events"
        schema_entry["message"] = schema_name
    
    registry['schemas'] = registry.get('schemas', []) + [schema_entry]
    save_registry(registry)
    
    print(f"\n[✅] Schema {schema_name} 创建成功")
    print(f"    文件: {file_rel_path}")
    print(f"    Topic: {topic}")

def version_new(args: argparse.Namespace) -> None:
    """创建 Schema 的新版本"""
    schema_name = args.name
    schema_version = args.version
    
    if not schema_name:
        print("[❌] 未提供 schema 名称")
        return
    
    if not schema_version:
        print("[❌] 未提供版本号")
        return
    
    print(f"\n[🔖] 创建 Schema 新版本: {schema_name} v{schema_version}")
    
    # 加载注册表
    registry = load_registry()
    
    # 查找现有 schema
    existing_schema = None
    for schema in registry.get('schemas', []):
        if schema.get('name') == schema_name:
            existing_schema = schema
            break
    
    if not existing_schema:
        print(f"[❌] Schema {schema_name} 不存在")
        return
    
    # 检查版本是否已存在
    current_version = existing_schema.get('version', '1')
    if current_version == str(schema_version):
        print(f"[❌] 版本 {schema_version} 已经存在")
        return
    
    # 确定格式和文件路径
    schema_format = existing_schema.get('format')
    original_file = existing_schema.get('file')
    schema_topic = existing_schema.get('topic')
    schema_desc = existing_schema.get('description', '')
    
    if not all([schema_format, original_file]):
        print(f"[❌] 现有 Schema 定义不完整")
        return
    
    # 创建新文件名（添加版本号）
    orig_file_path = Path(original_file)
    file_dir = orig_file_path.parent
    file_stem = orig_file_path.stem
    file_ext = orig_file_path.suffix
    
    # 创建版本号的文件名：例如 user_registered_v2.proto
    versioned_file_name = f"{file_stem}_v{schema_version}{file_ext}"
    versioned_file_path = os.path.join(file_dir, versioned_file_name)
    versioned_full_path = os.path.join(SCHEMA_DIR, versioned_file_path)
    
    # 复制原始文件作为新版本的起点
    original_full_path = os.path.join(SCHEMA_DIR, original_file)
    if not os.path.exists(original_full_path):
        print(f"[❌] 原始 Schema 文件不存在: {original_full_path}")
        return
    
    try:
        with open(original_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(versioned_full_path), exist_ok=True)
        
        # 写入新文件
        with open(versioned_full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[✅] 创建版本文件: {versioned_full_path}")
        
        # 创建新的注册表条目
        new_schema_entry = existing_schema.copy()
        new_schema_entry['name'] = f"{schema_name}V{schema_version}"
        new_schema_entry['file'] = versioned_file_path
        new_schema_entry['version'] = str(schema_version)
        new_schema_entry['parent'] = schema_name
        
        # 更新 topic（可选）
        if args.update_topic and schema_topic:
            topic_parts = schema_topic.split('/')
            if len(topic_parts) > 0:
                last_part = topic_parts[-1]
                new_last_part = f"{last_part}.v{schema_version}"
                topic_parts[-1] = new_last_part
                new_schema_entry['topic'] = '/'.join(topic_parts)
        
        # 添加到注册表
        registry['schemas'] = registry.get('schemas', []) + [new_schema_entry]
        save_registry(registry)
        
        print(f"\n[✅] Schema {schema_name} 版本 {schema_version} 创建成功")
        print(f"    文件: {versioned_file_path}")
        if args.update_topic:
            print(f"    Topic: {new_schema_entry.get('topic')}")
    except Exception as e:
        print(f"[❌] 创建新版本失败: {e}")

def version_list(args: argparse.Namespace) -> None:
    """列出 Schema 的所有版本"""
    schema_name = args.name
    
    if not schema_name:
        print("[❌] 未提供 schema 名称")
        return
    
    print(f"\n[📋] Schema {schema_name} 的版本列表:")
    
    # 加载注册表
    registry = load_registry()
    
    # 查找所有相关 schema
    original_schema = None
    versioned_schemas = []
    
    for schema in registry.get('schemas', []):
        if schema.get('name') == schema_name:
            original_schema = schema
        elif schema.get('parent') == schema_name:
            versioned_schemas.append(schema)
    
    if not original_schema:
        print(f"[❌] Schema {schema_name} 不存在")
        return
    
    # 打印主版本信息
    print(f"\n主版本:")
    print(f"  名称: {original_schema.get('name')}")
    print(f"  文件: {original_schema.get('file')}")
    print(f"  Topic: {original_schema.get('topic', 'N/A')}")
    print(f"  格式: {original_schema.get('format', 'N/A')}")
    print(f"  描述: {original_schema.get('description', 'N/A')}")
    
    # 打印衍生版本信息
    if versioned_schemas:
        print("\n衍生版本:")
        for schema in sorted(versioned_schemas, key=lambda s: s.get('version', '0')):
            version = schema.get('version', 'unknown')
            print(f"\n  版本 {version}:")
            print(f"    名称: {schema.get('name')}")
            print(f"    文件: {schema.get('file')}")
            print(f"    Topic: {schema.get('topic', 'N/A')}")
    else:
        print("\n没有找到衍生版本。")

def verify_compatibility(args: argparse.Namespace) -> None:
    """验证 Schema 的兼容性"""
    schema_name = args.name
    schema_version = args.version
    compat_mode = args.mode or "BACKWARD"
    
    if not schema_name:
        print("[❌] 未提供 schema 名称")
        return
    
    if not schema_version:
        print("[❌] 未提供版本号")
        return
    
    valid_modes = ["BACKWARD", "FORWARD", "FULL", "NONE"]
    if compat_mode not in valid_modes:
        print(f"[❌] 无效的兼容性模式: {compat_mode}")
        print(f"    有效模式: {', '.join(valid_modes)}")
        return
    
    print(f"\n[🔍] 验证 Schema 兼容性: {schema_name} v{schema_version} ({compat_mode})")
    
    # 加载注册表
    registry = load_registry()
    
    # 查找原始 schema
    original_schema = None
    versioned_schema = None
    
    for schema in registry.get('schemas', []):
        if schema.get('name') == schema_name:
            original_schema = schema
        elif schema.get('parent') == schema_name and schema.get('version') == str(schema_version):
            versioned_schema = schema
    
    if not original_schema:
        print(f"[❌] Schema {schema_name} 不存在")
        return
    
    if not versioned_schema:
        print(f"[❌] Schema {schema_name} 版本 {schema_version} 不存在")
        return
    
    # 获取文件路径
    original_file = original_schema.get('file')
    versioned_file = versioned_schema.get('file')
    schema_format = original_schema.get('format')
    
    if not all([original_file, versioned_file, schema_format]):
        print(f"[❌] Schema 定义不完整")
        return
    
    original_path = os.path.join(SCHEMA_DIR, original_file)
    versioned_path = os.path.join(SCHEMA_DIR, versioned_file)
    
    if not os.path.exists(original_path):
        print(f"[❌] 原始 Schema 文件不存在: {original_path}")
        return
    
    if not os.path.exists(versioned_path):
        print(f"[❌] 版本 Schema 文件不存在: {versioned_path}")
        return
    
    # 基于 schema 格式执行兼容性检查
    if schema_format == 'avro':
        verify_avro_compatibility(original_path, versioned_path, compat_mode)
    elif schema_format == 'proto':
        verify_proto_compatibility(original_path, versioned_path, compat_mode)
    elif schema_format == 'json':
        verify_json_compatibility(original_path, versioned_path, compat_mode)
    else:
        print(f"[❌] 不支持的 Schema 格式: {schema_format}")

def verify_avro_compatibility(original_path: str, versioned_path: str, mode: str) -> None:
    """验证 Avro schema 兼容性"""
    try:
        import json

        # 读取 schema 文件
        with open(original_path, 'r', encoding='utf-8') as f:
            original_schema = json.load(f)
        
        with open(versioned_path, 'r', encoding='utf-8') as f:
            versioned_schema = json.load(f)
        
        # 检查是否已安装 avro 库
        try:
            from avro.compatibility import SchemaCompatibility
            from avro.schema import SchemaParseException

            # 解析 schema
            original_parsed = json.dumps(original_schema)
            versioned_parsed = json.dumps(versioned_schema)
            
            # 根据模式验证兼容性
            if mode == "BACKWARD":
                # 新版本可以读取旧版本数据
                result = SchemaCompatibility.can_read(versioned_parsed, original_parsed)
                if result:
                    print("[✅] BACKWARD 兼容性测试通过: 新版本可以读取旧版本数据")
                else:
                    print("[❌] BACKWARD 兼容性测试失败: 新版本不能读取旧版本数据")
            
            elif mode == "FORWARD":
                # 旧版本可以读取新版本数据
                result = SchemaCompatibility.can_read(original_parsed, versioned_parsed)
                if result:
                    print("[✅] FORWARD 兼容性测试通过: 旧版本可以读取新版本数据")
                else:
                    print("[❌] FORWARD 兼容性测试失败: 旧版本不能读取新版本数据")
            
            elif mode == "FULL":
                # 双向兼容
                backward = SchemaCompatibility.can_read(versioned_parsed, original_parsed)
                forward = SchemaCompatibility.can_read(original_parsed, versioned_parsed)
                
                if backward and forward:
                    print("[✅] FULL 兼容性测试通过: 双向兼容")
                else:
                    print("[❌] FULL 兼容性测试失败")
                    if not backward:
                        print("    - BACKWARD 兼容性失败: 新版本不能读取旧版本数据")
                    if not forward:
                        print("    - FORWARD 兼容性失败: 旧版本不能读取新版本数据")
            
            else:  # "NONE"
                print("[ℹ️] 兼容性测试已跳过 (NONE 模式)")
        
        except ImportError:
            # 如果没有安装 avro 库，执行基本检查
            print("[⚠️] avro 库未安装，执行基本兼容性检查")
            basic_avro_compatibility_check(original_schema, versioned_schema, mode)
    
    except Exception as e:
        print(f"[❌] Avro 兼容性检查失败: {e}")

def basic_avro_compatibility_check(original_schema: dict, versioned_schema: dict, mode: str) -> None:
    """执行基本的 Avro 兼容性检查"""
    # 获取字段信息
    original_fields = {f['name']: f for f in original_schema.get('fields', [])}
    versioned_fields = {f['name']: f for f in versioned_schema.get('fields', [])}
    
    # 检查向后兼容性 (BACKWARD) - 新版本可以读取旧版本数据
    if mode in ["BACKWARD", "FULL"]:
        missing_fields = []
        incompatible_fields = []
        
        for name, field in original_fields.items():
            # 检查字段是否存在于新版本
            if name not in versioned_fields:
                # 如果新版本缺少旧版本的字段，必须有默认值
                if 'default' not in field:
                    missing_fields.append(name)
            else:
                # 检查类型兼容性
                v_field = versioned_fields[name]
                if not are_avro_types_compatible(field.get('type'), v_field.get('type')):
                    incompatible_fields.append(name)
        
        if missing_fields or incompatible_fields:
            print("[❌] BACKWARD 兼容性测试失败:")
            if missing_fields:
                print(f"    - 缺少必要字段: {', '.join(missing_fields)}")
            if incompatible_fields:
                print(f"    - 类型不兼容字段: {', '.join(incompatible_fields)}")
        else:
            print("[✅] BACKWARD 兼容性测试通过")
    
    # 检查向前兼容性 (FORWARD) - 旧版本可以读取新版本数据
    if mode in ["FORWARD", "FULL"]:
        problematic_fields = []
        
        for name, field in versioned_fields.items():
            # 检查新字段在旧版本中是否存在
            if name not in original_fields:
                # 如果新版本添加了字段，必须有默认值
                if 'default' not in field:
                    problematic_fields.append(f"{name} (缺少默认值)")
            else:
                # 检查类型兼容性
                o_field = original_fields[name]
                if not are_avro_types_compatible(o_field.get('type'), field.get('type')):
                    problematic_fields.append(f"{name} (类型不兼容)")
        
        if problematic_fields:
            print("[❌] FORWARD 兼容性测试失败:")
            print(f"    - 问题字段: {', '.join(problematic_fields)}")
        else:
            print("[✅] FORWARD 兼容性测试通过")

def are_avro_types_compatible(type1, type2) -> bool:
    """检查两个 Avro 类型是否兼容"""
    # 简化的兼容性检查
    if type1 == type2:
        return True
    
    # 处理 union 类型
    if isinstance(type1, list) and isinstance(type2, list):
        return set(type1).issubset(set(type2))
    
    # 处理复杂类型
    if isinstance(type1, dict) and isinstance(type2, dict):
        return type1.get('type') == type2.get('type')
    
    # 基本类型兼容对
    compatible_types = {
        'int': ['long', 'float', 'double'],
        'long': ['float', 'double'],
        'float': ['double']
    }
    
    if isinstance(type1, str) and isinstance(type2, str):
        if type2 in compatible_types.get(type1, []):
            return True
    
    return False

def verify_proto_compatibility(original_path: str, versioned_path: str, mode: str) -> None:
    """验证 Protocol Buffers schema 兼容性"""
    try:
        # 读取 proto 文件
        with open(original_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        with open(versioned_path, 'r', encoding='utf-8') as f:
            versioned_content = f.read()
        
        # 提取消息定义
        original_messages = extract_proto_messages(original_content)
        versioned_messages = extract_proto_messages(versioned_content)
        
        compatibility_issues = []
        
        # 执行兼容性检查
        for msg_name, original_fields in original_messages.items():
            if msg_name in versioned_messages:
                versioned_fields = versioned_messages[msg_name]
                
                # 检查字段
                for field_num, original_info in original_fields.items():
                    # 向后兼容性：原始字段必须存在或有默认值
                    if mode in ["BACKWARD", "FULL"]:
                        if field_num not in versioned_fields:
                            compatibility_issues.append(
                                f"消息 {msg_name} 的字段 {field_num} ({original_info['name']}) "
                                f"在新版本中缺失，不符合向后兼容性要求"
                            )
                        else:
                            # 字段类型不能改变
                            v_info = versioned_fields[field_num]
                            if original_info['type'] != v_info['type']:
                                compatibility_issues.append(
                                    f"消息 {msg_name} 的字段 {field_num} ({original_info['name']}) "
                                    f"类型从 {original_info['type']} 变为 {v_info['type']}，不符合兼容性要求"
                                )
                
                # 向前兼容性检查
                if mode in ["FORWARD", "FULL"]:
                    for field_num, v_info in versioned_fields.items():
                        if int(field_num) < 1000 and field_num not in original_fields:
                            compatibility_issues.append(
                                f"消息 {msg_name} 添加了新字段 {field_num} ({v_info['name']}) "
                                f"但未使用保留字段范围 (1000+)，可能不符合向前兼容性要求"
                            )
        
        # 输出结果
        if compatibility_issues:
            print(f"[❌] {mode} 兼容性检查失败:")
            for issue in compatibility_issues:
                print(f"    - {issue}")
        else:
            print(f"[✅] {mode} 兼容性检查通过")
    
    except Exception as e:
        print(f"[❌] Proto 兼容性检查失败: {e}")

def extract_proto_messages(content: str) -> dict:
    """
    从 Proto 文件内容中提取消息定义
    返回 {message_name: {field_number: {'name': field_name, 'type': field_type}}}
    """
    messages = {}
    
    # 匹配消息定义
    message_blocks = re.finditer(r'message\s+([A-Za-z0-9_]+)\s*{([^}]+)}', content)
    
    for block in message_blocks:
        message_name = block.group(1)
        message_body = block.group(2)
        
        fields = {}
        
        # 匹配字段定义
        for line in message_body.split('\n'):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            field_match = re.search(r'(repeated|optional|required)?\s*([A-Za-z0-9_.<>]+)\s+([A-Za-z0-9_]+)\s*=\s*(\d+)', line)
            if field_match:
                modifier = field_match.group(1) or ''
                field_type = field_match.group(2)
                field_name = field_match.group(3)
                field_num = field_match.group(4)
                
                fields[field_num] = {
                    'name': field_name,
                    'type': field_type,
                    'repeated': modifier == 'repeated',
                    'optional': modifier == 'optional' or not modifier,
                    'required': modifier == 'required'
                }
        
        messages[message_name] = fields
    
    return messages

def verify_json_compatibility(original_path: str, versioned_path: str, mode: str) -> None:
    """验证 JSON Schema 兼容性"""
    try:
        import json

        # 读取 schema 文件
        with open(original_path, 'r', encoding='utf-8') as f:
            original_schema = json.load(f)
        
        with open(versioned_path, 'r', encoding='utf-8') as f:
            versioned_schema = json.load(f)
        
        # 检查 required 字段
        original_required = set(original_schema.get('required', []))
        versioned_required = set(versioned_schema.get('required', []))
        
        # 获取属性
        original_props = original_schema.get('properties', {})
        versioned_props = versioned_schema.get('properties', {})
        
        compatibility_issues = []
        
        # 向后兼容性检查
        if mode in ["BACKWARD", "FULL"]:
            # 新 required 字段不能超过旧 required
            if not original_required.issubset(versioned_required):
                missing_required = original_required - versioned_required
                compatibility_issues.append(
                    f"新版本缺少必要字段: {', '.join(missing_required)}"
                )
            
            # 检查原始属性在新版本中是否存在且类型兼容
            for prop_name, prop_def in original_props.items():
                if prop_name not in versioned_props:
                    if prop_name in original_required:
                        compatibility_issues.append(
                            f"新版本缺少必要属性: {prop_name}"
                        )
                else:
                    # 检查类型兼容性
                    v_prop = versioned_props[prop_name]
                    if not are_json_types_compatible(prop_def, v_prop):
                        compatibility_issues.append(
                            f"属性 {prop_name} 的类型不兼容: "
                            f"{prop_def.get('type')} vs {v_prop.get('type')}"
                        )
        
        # 向前兼容性检查
        if mode in ["FORWARD", "FULL"]:
            # 新版本添加的属性如果是必需的，会破坏向前兼容性
            new_required = versioned_required - original_required
            new_props = set(versioned_props.keys()) - set(original_props.keys())
            problematic_props = new_required.intersection(new_props)
            
            if problematic_props:
                compatibility_issues.append(
                    f"新版本添加了必需属性: {', '.join(problematic_props)}"
                )
            
            # 检查类型兼容性
            for prop_name in set(original_props.keys()).intersection(set(versioned_props.keys())):
                o_prop = original_props[prop_name]
                v_prop = versioned_props[prop_name]
                
                if not are_json_types_compatible(o_prop, v_prop, reverse=True):
                    compatibility_issues.append(
                        f"属性 {prop_name} 的类型不兼容 (向前): "
                        f"{o_prop.get('type')} vs {v_prop.get('type')}"
                    )
        
        # 输出结果
        if compatibility_issues:
            print(f"[❌] {mode} 兼容性检查失败:")
            for issue in compatibility_issues:
                print(f"    - {issue}")
        else:
            print(f"[✅] {mode} 兼容性检查通过")
    
    except Exception as e:
        print(f"[❌] JSON 兼容性检查失败: {e}")

def are_json_types_compatible(type1: dict, type2: dict, reverse: bool = False) -> bool:
    """
    检查两个 JSON Schema 类型是否兼容
    reverse=True 时检查向前兼容性
    """
    # 如果反向检查，交换参数
    if reverse:
        type1, type2 = type2, type1
    
    # 获取类型
    t1 = type1.get('type')
    t2 = type2.get('type')
    
    # 类型相同则兼容
    if t1 == t2:
        return True
    
    # 数字类型兼容性
    if t1 == 'integer' and t2 == 'number':
        return True
    
    # 如果是数组，检查项目类型
    if t1 == 'array' and t2 == 'array':
        items1 = type1.get('items', {})
        items2 = type2.get('items', {})
        return are_json_types_compatible(items1, items2, reverse)
    
    # 对象类型特殊处理
    if t1 == 'object' and t2 == 'object':
        # 向后兼容性：新对象应接受所有旧对象属性
        props1 = type1.get('properties', {})
        props2 = type2.get('properties', {})
        
        for name, prop in props1.items():
            if name in props2:
                if not are_json_types_compatible(prop, props2[name], reverse):
                    return False
            elif name in type1.get('required', []):
                return False
        
        return True
    
    return False

def convert_json_type_to_avro(json_type, json_format=None):
    """将 JSON Schema 类型转换为 Avro 类型"""
    # 处理数组类型
    if isinstance(json_type, list):
        # JSON Schema 中的 ["null", "string"] 应转换为 Avro 中的 ["null", "string"]
        return json_type
    
    # 处理基本类型
    if json_type == "string":
        if json_format == "date-time" or json_format == "date":
            # 对于日期时间类型，使用 Avro 的 string 表示，并添加逻辑类型注解
            return {"type": "string", "logicalType": "timestamp-millis" if json_format == "date-time" else "date"}
        elif json_format == "uuid":
            return {"type": "string", "logicalType": "uuid"}
        elif json_format == "email":
            return {"type": "string", "logicalType": "email"}
        elif json_format == "uri":
            return {"type": "string", "logicalType": "uri"}
        return "string"
    elif json_type == "integer":
        if json_format == "int32":
            return "int"
        elif json_format == "int64":
            return "long"
        return "int"  # 默认使用 int
    elif json_type == "number":
        if json_format == "float":
            return "float"
        elif json_format == "double":
            return "double"
        return "double"  # 默认使用 double
    elif json_type == "boolean":
        return "boolean"
    elif json_type == "null":
        return "null"
    elif json_type == "array":
        # 对于数组类型，需要在调用处处理其项目类型
        return "array"
    elif json_type == "object":
        # 对于对象类型，需要在调用处处理其属性
        return "record"
    
    # 默认情况，使用字符串类型
    return "string"

def validate_avro_schema(avro_schema):
    """验证 Avro Schema 是否符合规范要求"""
    if not isinstance(avro_schema, dict):
        raise ValueError("Avro schema must be a dictionary")
    
    # 检查基本必须字段
    if "type" not in avro_schema:
        raise ValueError("Avro schema must contain 'type' field")
    
    if avro_schema["type"] == "record":
        # record 类型必须有 name 和 fields
        if "name" not in avro_schema:
            raise ValueError("Record schema must contain 'name' field")
        
        if "fields" not in avro_schema or not isinstance(avro_schema["fields"], list):
            raise ValueError("Record schema must contain 'fields' array")
        
        # 检查每个字段
        for field in avro_schema["fields"]:
            if "name" not in field:
                raise ValueError("Each field must have a 'name'")
            if "type" not in field:
                raise ValueError(f"Field {field.get('name', '?')} must have a 'type'")
    
    # 其他类型的验证可以根据需要添加
    
    return True

def json_schema_to_avro(json_schema, schema_name, namespace="com.idp.events"):
    """将 JSON Schema 转换为 Avro Schema"""
    if not isinstance(json_schema, dict):
        try:
            json_schema = json.loads(json_schema)
        except Exception as e:
            raise ValueError(f"Invalid JSON Schema: {e}")
    
    # 创建基本的 Avro 记录结构
    avro_schema = {
        "type": "record",
        "name": schema_name,
        "namespace": namespace,
        "fields": []
    }
    
    # 添加文档说明
    if "description" in json_schema:
        avro_schema["doc"] = json_schema.get("description")
    elif "title" in json_schema:
        avro_schema["doc"] = json_schema.get("title")
    
    # 定义一个辅助函数来创建唯一的嵌套记录名称
    def create_nested_name(parent_name, field_name):
        # 首字母大写
        field_name = field_name[0].upper() + field_name[1:] if field_name else ""
        return f"{parent_name}{field_name}"
    
    # 定义一个辅助函数来处理嵌套对象
    def process_object_field(parent_name, field_name, obj_def, required=False):
        # 创建嵌套记录类型
        nested_name = create_nested_name(parent_name, field_name)
        nested_record = {
            "type": "record",
            "name": nested_name,
            "fields": []
        }
        
        # 添加嵌套对象的文档
        if "description" in obj_def:
            nested_record["doc"] = obj_def.get("description")
        
        # 处理嵌套对象的属性
        if "properties" in obj_def and isinstance(obj_def["properties"], dict):
            nested_required = obj_def.get("required", [])
            
            for prop_name, prop_def in obj_def["properties"].items():
                is_prop_required = prop_name in nested_required
                nested_field = process_field(nested_name, prop_name, prop_def, is_prop_required)
                if nested_field:
                    nested_record["fields"].append(nested_field)
        
        # 如果没有字段，添加一个虚拟字段
        if not nested_record["fields"]:
            nested_record["fields"].append({
                "name": "placeholder",
                "type": "string",
                "doc": "Placeholder field"
            })
        
        # 对于可选字段，使用 union 类型
        if not required:
            return {"name": field_name, "type": ["null", nested_record], "default": None}
        else:
            return {"name": field_name, "type": nested_record}
    
    # 定义一个辅助函数来处理数组类型
    def process_array_field(parent_name, field_name, array_def, required=False):
        items = array_def.get("items", {})
        item_type = items.get("type", "string")
        
        # 处理数组项目类型
        if item_type == "object":
            # 为数组中的对象类型创建嵌套记录
            nested_name = create_nested_name(parent_name, field_name + "Item")
            item_type_obj = process_object_field(parent_name, nested_name, items, True)
            
            # 使用嵌套记录的类型定义
            array_type = {
                "type": "array",
                "items": item_type_obj["type"] if required else item_type_obj["type"][1]  # 选择非 null 类型
            }
        else:
            # 处理基本类型的数组
            avro_item_type = convert_json_type_to_avro(item_type, items.get("format"))
            array_type = {
                "type": "array",
                "items": avro_item_type
            }
        
        # 对于可选字段，使用 union 类型
        if not required:
            return {"name": field_name, "type": ["null", array_type], "default": None}
        else:
            return {"name": field_name, "type": array_type}
    
    # 定义一个辅助函数来处理枚举类型
    def process_enum_field(parent_name, field_name, enum_def, required=False):
        enum_values = enum_def.get("enum", [])
        # 确保枚举值是字符串且符合 Avro 要求
        enum_values = [str(v) for v in enum_values]
        
        # 创建枚举类型
        enum_type = {
            "type": "enum",
            "name": create_nested_name(parent_name, field_name + "Enum"),
            "symbols": enum_values
        }
        
        # 对于可选字段，使用 union 类型
        if not required:
            return {"name": field_name, "type": ["null", enum_type], "default": None}
        else:
            return {"name": field_name, "type": enum_type}
    
    # 定义一个统一的字段处理函数
    def process_field(parent_name, field_name, field_def, required=False):
        field_type = field_def.get("type", "string")
        
        # 处理不同类型的字段
        if field_type == "object":
            return process_object_field(parent_name, field_name, field_def, required)
        elif field_type == "array":
            return process_array_field(parent_name, field_name, field_def, required)
        elif "enum" in field_def:
            return process_enum_field(parent_name, field_name, field_def, required)
        else:
            # 处理基本类型
            avro_type = convert_json_type_to_avro(field_type, field_def.get("format"))
            
            field = {
                "name": field_name,
                "doc": field_def.get("description", f"Field {field_name}")
            }
            
            # 对于可选字段，使用 union 类型
            if not required:
                field["type"] = ["null", avro_type]
                field["default"] = None
            else:
                field["type"] = avro_type
            
            return field
    
    # 从 JSON Schema 的 properties 转换为 Avro 字段
    properties = json_schema.get("properties", {})
    required_fields = json_schema.get("required", [])
    
    for prop_name, prop_def in properties.items():
        is_required = prop_name in required_fields
        field = process_field(schema_name, prop_name, prop_def, is_required)
        if field:
            avro_schema["fields"].append(field)
    
    # 如果没有字段，添加一个虚拟字段
    if not avro_schema["fields"]:
        avro_schema["fields"].append({
            "name": "placeholder",
            "type": "string",
            "doc": "Placeholder field"
        })
    
    # 验证生成的 Avro Schema
    try:
        # 简化验证，这里只检查最基本的结构
        if avro_schema["type"] != "record" or not avro_schema.get("fields"):
            raise ValueError("Invalid AVRO schema structure")
        
        # 确保不存在重复命名的记录类型
        record_names = set()
        
        def check_record_names(schema_obj):
            if isinstance(schema_obj, dict):
                if schema_obj.get("type") == "record":
                    name = schema_obj.get("name")
                    if name in record_names:
                        raise ValueError(f"Duplicate record name: {name}")
                    record_names.add(name)
                    
                    # 递归检查字段
                    for field in schema_obj.get("fields", []):
                        field_type = field.get("type")
                        if isinstance(field_type, list):
                            for t in field_type:
                                check_record_names(t)
                        else:
                            check_record_names(field_type)
        
        check_record_names(avro_schema)
        
    except ValueError as e:
        print(f"[⚠️] 生成的 Avro Schema 不符合规范: {e}")
        print(f"[⚠️] 尝试修复并继续...")
    
    return avro_schema

def main():
    parser = argparse.ArgumentParser(description="Schema 管理工具")
    subparsers = parser.add_subparsers(dest="command", help="要执行的命令")
    
    # build 命令
    build_parser = subparsers.add_parser("build", help="编译所有 schema")
    build_parser.set_defaults(func=build_schemas)
    
    # generate 命令
    generate_parser = subparsers.add_parser("generate", help="生成 Pydantic 模型")
    generate_parser.set_defaults(func=generate_models)
    
    # register 命令
    register_parser = subparsers.add_parser("register", help="注册 schema 到 Schema Registry")
    register_parser.add_argument("--url", help="Pulsar 管理 API URL")
    register_parser.set_defaults(func=register_schemas)
    
    # docs 命令
    docs_parser = subparsers.add_parser("docs", help="生成 schema 文档")
    docs_parser.set_defaults(func=generate_docs)
    
    # create 命令
    create_parser = subparsers.add_parser("create", help="创建新的 schema")
    create_parser.add_argument("--name", required=True, help="Schema 名称")
    create_parser.add_argument("--format", default="proto", choices=["proto", "avro", "json"], help="Schema 格式")
    create_parser.add_argument("--desc", help="Schema 描述")
    create_parser.set_defaults(func=create_schema)
    
    # version-new 命令
    version_new_parser = subparsers.add_parser("version-new", help="创建 Schema 的新版本")
    version_new_parser.add_argument("--name", required=True, help="Schema 名称")
    version_new_parser.add_argument("--version", required=True, help="版本号")
    version_new_parser.add_argument("--update-topic", action="store_true", help="更新 topic 名称以包含版本号")
    version_new_parser.set_defaults(func=version_new)
    
    # version-list 命令
    version_list_parser = subparsers.add_parser("version-list", help="列出 Schema 的所有版本")
    version_list_parser.add_argument("--name", required=True, help="Schema 名称")
    version_list_parser.set_defaults(func=version_list)
    
    # verify-compatibility 命令
    verify_parser = subparsers.add_parser("verify-compatibility", help="验证 Schema 的兼容性")
    verify_parser.add_argument("--name", required=True, help="Schema 名称")
    verify_parser.add_argument("--version", required=True, help="版本号")
    verify_parser.add_argument("--mode", choices=["BACKWARD", "FORWARD", "FULL", "NONE"], 
                               default="BACKWARD", help="兼容性模式")
    verify_parser.set_defaults(func=verify_compatibility)
    
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
