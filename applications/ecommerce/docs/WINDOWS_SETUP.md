# Windows 环境安装指南

## 安装 asyncpg（PostgreSQL 驱动）

### 问题

在 Windows 上安装 `asyncpg` 时出现错误：

```
error: Microsoft Visual C++ 14.0 or greater is required.
```

### 解决方案

#### 方法 1: 安装 Microsoft C++ Build Tools（推荐）

**下载地址**: https://visualstudio.microsoft.com/visual-cpp-build-tools/

或直接下载: https://aka.ms/vs/17/release/vs_BuildTools.exe

**安装步骤**:

1. **运行安装程序**
   - 双击下载的 `vs_BuildTools.exe`

2. **选择工作负载**
   - 在 "Workloads" 选项卡中
   - 勾选 **"Desktop development with C++"**

3. **确认组件**（右侧面板）
   - ✅ MSVC v143 - VS 2022 C++ x64/x86 build tools (Latest)
   - ✅ Windows 11 SDK (或 Windows 10 SDK)
   - ✅ C++ CMake tools for Windows

4. **安装**
   - 点击右下角的 "Install"
   - 需要约 2-3 GB 磁盘空间
   - 安装时间约 10-15 分钟

5. **重启电脑**（重要！）

6. **验证安装**
   ```powershell
   # 打开新的 PowerShell 窗口
   cl
   # 应该显示 Microsoft C/C++ 编译器信息
   ```

7. **重新安装 asyncpg**
   ```powershell
   cd D:\workspace\repo\bento\applications\ecommerce
   
   # 取消注释 requirements.txt 中的 asyncpg
   # asyncpg>=0.29.0
   
   # 重新安装
   uv pip install -r requirements.txt
   ```

---

#### 方法 2: 安装 Visual Studio Community

如果你想要完整的 IDE（不仅仅是编译工具）：

**下载地址**: https://visualstudio.microsoft.com/vs/community/

**安装步骤**:

1. 运行安装程序
2. 选择 **"Desktop development with C++"** workload
3. 安装（需要约 5-10 GB 空间）
4. 重启电脑
5. 重新安装 asyncpg

---

### 验证 asyncpg 安装

```powershell
# 在虚拟环境中
python -c "import asyncpg; print(asyncpg.__version__)"
```

如果显示版本号（如 `0.30.0`），说明安装成功！

---

## 常见问题

### Q: 我必须安装 Visual Studio 吗？

A: 不必须。只需安装 **Build Tools** 即可（方法 1），它更小更快。

### Q: 安装 Build Tools 需要多少空间？

A: 大约 2-3 GB。完整的 Visual Studio 需要 5-10 GB。

### Q: 我可以不安装吗？

A: 可以！如果只用 SQLite，不需要安装。测试环境使用 SQLite，不需要 asyncpg。

### Q: 安装后还是失败怎么办？

A: 
1. 确保重启了电脑
2. 打开新的 PowerShell 窗口
3. 确认 `cl` 命令可用
4. 尝试升级 pip: `python -m pip install --upgrade pip`

---

## 替代方案：使用 Docker

如果你不想在 Windows 上安装编译工具，可以使用 Docker：

```dockerfile
# Dockerfile
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "applications.ecommerce.main:app", "--host", "0.0.0.0"]
```

```bash
# 构建和运行
docker build -t ecommerce-app .
docker run -p 8000:8000 ecommerce-app
```

---

## 总结

| 方案 | 磁盘空间 | 安装时间 | 推荐度 |
|------|---------|---------|-------|
| **Build Tools** | 2-3 GB | 10-15 分钟 | ⭐⭐⭐⭐⭐ |
| **Visual Studio** | 5-10 GB | 30-60 分钟 | ⭐⭐⭐ |
| **Docker** | ~1 GB | 5 分钟 | ⭐⭐⭐⭐ |
| **不安装**（用 SQLite） | 0 GB | 0 分钟 | ⭐⭐⭐⭐ |

**建议**: 
- 测试/开发阶段：使用 SQLite，不安装
- 生产环境：安装 Build Tools 或使用 Docker

