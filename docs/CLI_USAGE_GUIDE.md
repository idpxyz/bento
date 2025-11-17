# Bento CLI 使用指南

## 快速开始

```bash
cd /workspace/bento
PYTHONPATH=/workspace/bento/src python3 -m bento.toolkit.cli gen module User --fields "name:str,email:str"
```

## 生成完整模块（推荐）

```bash
# 用户模块
bento gen module User --fields "name:str,email:str,age:int"

# 订单模块  
bento gen module Order --fields "customer_id:str,total:float,status:str"
```

## 生成的文件

- domain/user.py - 聚合根（业务逻辑）
- infrastructure/models/user_po.py - 数据库模型
- infrastructure/mappers/user_mapper.py - 映射器（自动）
- infrastructure/repositories/user_repository.py - 仓储（自动）
- application/usecases/create_user.py - 用例
- domain/events/usercreated_event.py - 事件

## 开发人员只需要

1. 在聚合根添加业务方法
2. 在 UseCase 实现 handle() 方法
3. 其他由框架自动处理
