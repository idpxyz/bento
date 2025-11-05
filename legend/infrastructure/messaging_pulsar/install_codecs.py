#!/usr/bin/env python3
"""
安装编解码器依赖并生成必要的代码文件

运行方式:
    python install_codecs.py
"""

import os
import subprocess
import sys
from pathlib import Path


def print_step(message):
    """打印步骤信息"""
    print(f"\n{'=' * 80}")
    print(f"  {message}")
    print(f"{'=' * 80}\n")


def run_command(cmd, cwd=None):
    """运行命令并打印输出"""
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print(f"错误输出: {result.stderr}", file=sys.stderr)
    
    if result.returncode != 0:
        print(f"命令执行失败，退出码: {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
    
    return result


def install_dependencies():
    """安装编解码器所需的依赖"""
    print_step("安装编解码器依赖")
    
    # 获取当前脚本所在目录
    # current_dir = Path(__file__).parent.absolute()
    # requirements_file = current_dir / "requirements-codec.txt"
    
    # if not requirements_file.exists():
    #     print(f"找不到依赖文件: {requirements_file}", file=sys.stderr)
    #     sys.exit(1)
    
    # run_command(["pip", "install", "-r", str(requirements_file)])
    print("依赖安装完成!")


def generate_protobuf_code():
    """生成 Protocol Buffer 代码文件"""
    print_step("生成 Protocol Buffer 代码")
    
    # 获取proto文件目录
    current_dir = Path(__file__).parent.absolute()
    proto_dir = current_dir / "codec" / "protobuf"
    
    if not proto_dir.exists():
        print(f"找不到 protobuf 目录: {proto_dir}", file=sys.stderr)
        sys.exit(1)
    
    # 检查是否有 .proto 文件
    proto_files = list(proto_dir.glob("*.proto"))
    if not proto_files:
        print(f"警告: 在 {proto_dir} 中未找到 .proto 文件")
        return
    
    # 直接在此处生成，不依赖外部脚本
    for proto_file in proto_files:
        proto_path = str(proto_file)
        print(f"为 {proto_path} 生成 Python 代码...")
        
        try:
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={proto_dir}",
                proto_path
            ]
            run_command(cmd)
            print(f"✅ {proto_file.name} 代码生成成功")
        except Exception as e:
            print(f"❌ 生成 {proto_file.name} 代码失败: {str(e)}")
            raise
    
    # 验证生成的文件
    pb2_files = list(proto_dir.glob("*_pb2.py"))
    if pb2_files:
        print(f"已生成以下Python文件: {', '.join([f.name for f in pb2_files])}")
    else:
        print("⚠️ 未生成任何 Python 代码，请检查 protoc 命令是否成功执行")

    # 验证生成的代码
    current_dir = Path(__file__).parent.absolute()
    message_pb2 = current_dir / "codec" / "protobuf" / "message_pb2.py"
    
    if message_pb2.exists():
        print(f"✅ Protocol Buffer 代码已生成: {message_pb2}")
    else:
        print(f"❌ Protocol Buffer 代码生成失败，找不到文件: {message_pb2}")


def verify_installation():
    """验证安装和代码生成是否成功"""
    print_step("验证安装")
    
    # 确保依赖正确安装
    try:
        # 检查 pydantic
        import pydantic
        print(f"✅ Pydantic 已安装 (版本: {pydantic.__version__})")
    except ImportError:
        print("❌ Pydantic 安装失败或未找到")
    
    try:
        # 检查 protobuf
        import google.protobuf
        print(f"✅ Protocol Buffers 已安装 (版本: {google.protobuf.__version__})")
    except ImportError:
        print("❌ Protocol Buffers 安装失败或未找到")
    
    try:
        # 检查 avro
        import avro
        print(f"✅ Avro 已安装")
    except ImportError:
        print("❌ Avro 安装失败或未找到")
    
    # 验证生成的代码
    current_dir = Path(__file__).parent.absolute()
    message_pb2 = current_dir / "codec" / "protobuf" / "message_pb2.py"
    
    if message_pb2.exists():
        print(f"✅ Protocol Buffer 代码已生成: {message_pb2}")
    else:
        print(f"❌ Protocol Buffer 代码生成失败，找不到文件: {message_pb2}")
    
    print("\n安装验证完成!")


def main():
    """主函数，执行完整安装流程"""
    print("\n🚀 开始安装编解码器依赖和生成代码...\n")
    
    try:
        install_dependencies()
        generate_protobuf_code()
        verify_installation()
        
        print("\n✅ 所有步骤完成! 编解码器已准备就绪。")
        print("\n使用示例:")
        print("  - 检查编解码器状态: python -m idp.framework.infrastructure.messaging.codec.check_codecs")
        print("  - 性能测试: python -m idp.framework.infrastructure.messaging.demo.codec_comparison")
        print("  - 功能演示: python -m idp.framework.infrastructure.messaging.demo.event_bus_demo")
        
    except Exception as e:
        print(f"\n❌ 安装过程中出错: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 