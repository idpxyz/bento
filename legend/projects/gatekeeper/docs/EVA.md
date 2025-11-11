## 评估结论

> **总体进步明显**：
>
> 1. 绝大部分 **用户 / 角色 / 组织 CRUD 与登录流** 都已从 Gatekeeper 剥离，改为走 Logto Management API（M2M 模式）。
> 2. Gatekeeper 的核心职责被重塑为 **“业务策略 + 审计聚合 + 事件编排”**，并在代码与目录结构上落地。
> 3. 子应用通过轻量 `GatekeeperClient` 只调用策略/审计接口，整体依赖面大幅缩减。

> **仍需收尾的 4 个重点**：
> *A. 职责收敛一致性* *B. M2M Token 生命周期* *C. 前/后端权限栈闭环* *D. 可观测 & 回滚*。

---

### A. 职责收敛仍有\*\*“回弹”\*\*现象

* 在同一文档后半部，Gatekeeper 又出现 “统一认证 / 用户管理 / 租户管理”等完整 IAM 职责描述，并暴露 `/api/auth/login|refresh|logout` 等接口。
* 这与前文“只做策略 & 审计”的定位相冲突，若不清理，**功能重复**风险依旧。

**建议**

1. **删除** Gatekeeper 中的 `auth_service.py`、`user_service.py`、`tenant_service.py` 以及对应路由；只保留 `policy_service / audit_service / event_handler`。
2. `/api/auth/*` 路由全部 30x 跳转到 Logto OIDC 端点，让浏览器直接完成登录。

---

### B. M2M Access Token 的**获取与续签**

* 代码中直接把 `LOGTO_M2M_TOKEN` 填进 `createManagementApi` 参数。Access Token 通常 5–10 分钟即过期，**固定环境变量很快失效**。

**改进办法**

```python
async def _get_m2m_token():
    # 调 OIDC token 端点换取短期 access_token
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("LOGTO_M2M_ID"),
        "client_secret": os.getenv("LOGTO_M2M_SECRET"),
        "scope": "management:read management:write",
    }
    r = await httpx.post(f"{ISSUER}/oidc/token", data=data, timeout=5)
    ...
```

> 并用 `cachetools.TTLCache` 缓存到过期前 60 秒刷新一次。

---

### C. 权限链要做到**端到端闭环**

1. **Gateway 侧**：`Scope → Policy` 转换规则需集中存放（例如 YAML / DB），便于 DevOps 灰度变更；文档中只见函数示例，缺少配置来源。
2. **前端**：Refine / MUI 界面需要读取同一 Policy 结果（或直接读 scope）以隐藏无权限按钮，否则用户会频繁看到 403。
3. **审计**：`AuditService` 写入统一表时，建议同时记录 `principal.sub`, `org_id`, `scope_snapshot`，方便事后溯源。

---

### D. 可观测 & 运维

| 项           | 建议                                                                                              |
| ----------- | ----------------------------------------------------------------------------------------------- |
| **指标**      | 在 Gatekeeper 加 OTEL span `policy.evaluate`、`audit.write`；Prom 汇总 `policy_denied_total{reason}`。 |
| **发布**      | Helm Chart 中开启 `helm.sh/hook: pre-rollback`，确保回滚 Gatekeeper 时不会因为 DB schema drift 而失败。          |
| **回压 / 重放** | `event_handler` 处理 Logto Webhook 时应实现 *幂等键*（event-id）+ 重试队列；否则失败事件丢失。                           |

---

## 调整后可落地的 **最小 Gatekeeper 路由清单**

| 路由                 | 方法   | 说明               |
| ------------------ | ---- | ---------------- |
| `/policy/evaluate` | POST | 业务策略评估           |
| `/audit/events`    | GET  | 查询审计事件           |
| `/webhook/logto`   | POST | Logto Webhook 入站 |
| `/events/ms`       | POST | 微服务自定义事件         |

> 其余身份相关 API 全走 Logto；子应用若需用户列表，直接调用 Logto Management API。

---

## 结语

* **方向正确**：已把 Logto 当唯一 IAM，Gatekeeper 专注策略 + 审计。
* **剩余工作**：彻底移除残留登录 & 用户接口、改用动态 M2M Token，并补全观测 / 回滚。
* 完成上述精简后，Gatekeeper 将完全脱离 IAM 重复实现，真正成为轻量的企业策略层，后期维护与安全面将进一步收敛。
