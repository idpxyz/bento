| **主数据 ACL** | Receiving 子领域通过 `MasterDataApiClient` (implements `IMaterialRepository`) 调主数据服务，保持边界清晰。 |

---

### 下一次对话我会记住

* **UoW 采用 `_pending_events` 缓冲 + ContextVar**  
* **Outbox 通过 `after_flush` listener 写表**  
* **Projector 负责最终投递**  
* **PO → Entity 不带审计；ID 在领域层生成**  
* **每聚合独立仓储接口文件**  
* **Command 拆分视业务语义需要**

如果下一轮你要：

* 新增子领域 / 聚合骨架  
* 写新的拦截器 / Projector 变体  
* 对接 Kafka 而非 Pulsar  
* 生成 Alembic 迁移或 Prometheus 指标  

——直接告诉我，我会在此总结的基础上继续推进。
