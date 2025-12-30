以下为 **LOMS 完整 BC（Bounded Context）设计说明书（v1.0.0 冻结建议稿）**。本文面向“可落盘、可协同开发、可演进”的交付目标：给出 BC 列表、边界、核心概念、聚合与状态机归属、命令/事件与依赖关系、数据与集成策略，以及实施顺序与治理规则。
（术语约定：业务上的“发运/履约订单”统一命名为 **FulfillmentRequest（FR）/ShippingRequest**；执行对象为 **Shipment / Leg**。）

---

# 1. 文档目的与范围

## 1.1 目的

1. 为 LOMS 建立**清晰且可执行的限界上下文划分**，避免概念污染与代码耦合。
2. 让 contracts v1.0.0 的 **state machines / reason-codes / event routing** 能够落到工程结构中。
3. 支持你们跨境全链路场景：国内运输→国内仓→出口→国际→进口→海外运输→海外仓→末端。
4. 支持你们商业模式：多 broker/多 carrier/多仓、统一 API、对外 SaaS、可拆分产品矩阵（未来 Network Planning Engine 等独立售卖）。

## 1.2 范围

* LOMS 单体服务内的多 BC（初期“同服务多 BC”，未来可拆成多服务）。
* 与外部系统的集成采用 ACL（Anti-Corruption Layer）。
* 不包含 WMS/TMS/FMS 的完整能力，但包含与其集成所需的 Contract 与 Orchestration。

---

# 2. LOMS 的核心对象与边界原则

## 2.1 三层核心对象

1. **FulfillmentRequest（FR）**：需求/意图对象（客户侧）。
2. **Shipment**：执行对象（票/件/箱/包的执行状态机承载体）。
3. **Leg**：运输段执行对象（国内/出口/干线/进口/海外/末端等分段）。

## 2.2 边界原则（必须执行）

* **FR ≠ Shipment**：FR 是意图；Shipment 是执行。FR 允许版本化与变更；Shipment 关注执行状态与一致性。
* **BC 内部强一致，BC 之间最终一致**：跨 BC 通过事件或 ACL。
* **外部差异不进入领域**：承运商/仓/报关/面单 API 差异全部隔离在 Integration BC（ACL）。
* **禁止跨 BC 引用对方 domain**：跨 BC 只能订阅事件或调用对方公开应用接口（同服务可内部调用应用服务，但仍需遵守边界）。
* **Contract-as-Code 门禁**：reason-codes、state machine、event schema、routing matrix 作为 CI 门禁；实现必须与合同一致。

---

# 3. BC 全量目录（v1.0.0 建议冻结）

按业务闭环从“需求→执行→证据→商业结算→网络主数据→平台”划分 15 个 BC：

## 3.1 Demand & Intake（需求接入域）

1. **Fulfillment Request BC（FR BC）**
2. **Channel Intake BC（可选，若你们有多渠道导入/批量/文件）**

## 3.2 Core Execution（执行核心域）

3. **Shipment Execution BC**
4. **Leg Execution BC**
5. **Orchestration BC**

## 3.3 Evidence & Operations（证据与运营域）

6. **Document BC**
7. **Tracking BC**
8. **Exception & Operations BC（Issue/Reason/Case）**

## 3.4 Commercial（商业闭环域）

9. **Rating & Quotation BC（计价/报价）**
10. **Billing & Settlement BC（计费/对账/结算）**

## 3.5 Network & Master Data（网络与主数据域）

11. **Provider Management BC（服务商/账号/能力）**
12. **Network Planning BC（节点/线路/覆盖/时效）**
13. **Logistics Product BC（线路产品/服务产品）**

## 3.6 Integration & Platform（集成与平台域）

14. **Integration BC（ACL：Carrier/Broker/Warehouse/Customs）**
15. **Tenant & Configuration BC（租户/配置/Feature Flags/审计）**
    （Auth 可接 Gatekeeper，但 LOMS 仍保留最小租户/配置能力）

---

# 4. 各 BC 设计说明（逐一给出：定位、边界、聚合、命令、事件、依赖）

## 4.1 Fulfillment Request BC（FR BC）

### 定位

承载“客户履约意图”的全生命周期：接收、校验、归一化、去重、版本化、取消、变更，并建立与执行对象（Shipment）的映射关系。

### 边界

* FR BC 不关心运输分段细节，不直接管理 Leg。
* FR BC 通过 Orchestration 生成或调整 Shipment/Leg。
* FR 的状态机不等同 Shipment 状态机。

### 核心聚合

* `FulfillmentRequest`（聚合根）

  * 实体：`RequestLine`、`Party`、`AddressRef/AddressSnapshot`、`CustomsInfo`（如需）
  * 值对象：`FRId`、`RequestStatus`、`ChannelRef`、`Money`、`Incoterms`、`PackageSpec`

* `FulfillmentAllocation`（关系聚合或关系实体，强烈建议持久化并版本化）

  * `fr_id` ↔ `shipment_id`（多对多）
  * `allocation_type`（MERGE/SPLIT/PARTIAL）
  * `allocation_metrics`（重量/件数/价值/体积等）

### 关键命令

* `CreateFulfillmentRequest`
* `ReviseFulfillmentRequest`（产生新版本）
* `CancelFulfillmentRequest`
* `AllocateToShipment` / `DeallocateFromShipment`（由 Orchestration/运营触发）
* `CloseFulfillmentRequest`（当全部分配完成或取消）

### 关键事件

* `FulfillmentRequestCreated/Revised/Cancelled/Closed`
* `FulfillmentAllocationChanged`

### 依赖

* 读：Logistics Product（选择服务产品）、Network/Provider（校验覆盖）
* 写：不直接写 Shipment；由 Orchestration 统一执行映射

---

## 4.2 Shipment Execution BC

### 定位

LOMS 执行核心：承载 Shipment 状态机、Hold/Cancel/Exception、与 Leg 的绑定关系、幂等与一致性。

### 核心聚合

* `Shipment`（聚合根）

  * 实体：`ShipmentHold`、`ShipmentReference`、`ShipmentPartySnapshot`、`ShipmentLegLink`
  * 值对象：`ShipmentId`、`ShipmentCode`、`ShipmentStatus`、`HoldTypeCode`

### 关键命令（示例）

* `CreateShipment` / `UpdateShipmentBasics`
* `PlaceHold` / `ReleaseHold`
* `CancelShipment`
* `AttachLeg` / `DetachLeg`
* `RaiseShipmentException`（携带 reason_code）

### 关键事件

* `ShipmentCreated`
* `ShipmentStatusChanged`
* `ShipmentHoldPlaced/Released`
* `ShipmentCancelled`
* `ShipmentExceptionRaised`
* `ShipmentLegAttached/Detached`

### 依赖

* 订阅：Leg 状态事件以推进 Shipment（可由 Orchestration 负责推进，Shipment BC 只提供命令接口）
* 写外部：禁止；所有外部动作通过 Leg/Integration

---

## 4.3 Leg Execution BC

### 定位

每一段运输的执行状态机与动作：派单、揽收、交接、清关、入仓、出仓、签收、失败重试、换号等。

### 核心聚合

* `Leg`（聚合根）

  * 实体：`LegStop`、`LegAssignment`、`LegTrackingRef`、`LegDocumentRef`
  * 值对象：`LegId`、`LegType`、`LegStatus`、`ServiceLevel`、`TimeWindow`

### 关键命令

* `CreateLeg` / `UpdateLegPlan`
* `AssignProvider` / `ReassignProvider`
* `DispatchLeg`
* `ConfirmPickup` / `ConfirmDelivery`
* `FailLeg` / `RetryLeg` / `RerouteLeg`
* `SwapTrackingNumber`（换号）
* `BindDocument`（与 Document BC 关系）

### 关键事件

* `LegCreated`
* `LegStatusChanged`
* `LegDispatched`
* `LegFailed/Retried`
* `TrackingNumberAssigned/Swapped`

### 依赖

* 写外部：通过 Integration BC 下发任务/调用 API
* 读：Provider/Network/Product（可通过 Orchestration 提供决策输入）

---

## 4.4 Orchestration BC

### 定位

将 FR 的意图转为 Shipment+Leg 计划并驱动执行；订阅异常事件进行重规划；承担“策略决策”与“跨 BC 事务编排”。

### 核心对象（两种实现形态）

* 形态 A（推荐）：应用层编排为主，计划不作为强聚合持久化，只记录“决策事件”。
* 形态 B：`OrchestrationPlan` 聚合（若你们要求计划版本、可回溯、可审计）。

### 关键命令/用例

* `PlanFromFulfillmentRequest`（FR → Shipment+Leg）
* `ReplanOnException`（基于 reason-code 与策略重算）
* `SelectProviderForLeg`（选择承运商/仓/报关）
* `SyncExecutionProgress`（把 Leg 进度映射回 Shipment/FR）

### 关键事件

* `ShipmentPlanned/Replanned`
* `LegPlanUpdated`
* `ProviderSelected`（可选）

### 依赖

* 读：Network/Provider/Product/Rating
* 写：调用 Shipment/Leg 的 command handler（同服务内部调用或通过消息）
* 订阅：Exception/Integration/Leg/Shipment 的状态变更事件

---

## 4.5 Document BC

### 定位

面单/提单/商业发票/清关资料等文档的生成、版本化、作废、与 Shipment/Leg 的绑定，以及存储引用管理。

### 核心聚合

* `Document`（聚合根：类型、版本、状态、存储地址、hash、元数据）
* （可选）`DocumentTemplate`（模板版本与渲染参数）

### 关键命令

* `CreateDocument` / `RegenerateDocument`
* `VoidDocument`
* `BindDocumentToLeg/Shipment`

### 关键事件

* `DocumentCreated/Versioned/Voided`
* `DocumentBound`

### 依赖

* Integration BC：调用 label/customs API
* Storage：S3/MinIO（平台能力）

---

## 4.6 Tracking BC

### 定位

统一接入与聚合轨迹事件：去重、排序、规范化、生成 timeline，支持查询与推送。

### 核心聚合

* `TrackingStream`（按 shipment_id 或 leg_id 聚合）

### 关键命令

* `IngestTrackingEvent`
* `NormalizeTrackingEvent`
* `PublishTrackingTimeline`

### 关键事件

* `TrackingEventReceived`
* `TrackingTimelineUpdated`

### 依赖

* Integration BC：承运商轨迹回调/拉取
* 订阅 Leg/Shipment 的执行事件用于补全 timeline

---

## 4.7 Exception & Operations BC（Issue/Reason/Case）

### 定位

把异常产品化：reason-code 归类、处理策略、工单/人工介入、升级与 SLA。

### 核心聚合

* `OperationalIssue`（异常单/工单）
* `ResolutionAction`（处理动作：重试、改派、补资料等）

### 关键命令

* `OpenIssue` / `EscalateIssue` / `ResolveIssue`
* `AttachEvidence`（关联文档/日志/外部返回）

### 关键事件

* `IssueOpened/Escalated/Resolved`

### 依赖

* 订阅 Shipment/Leg/Document/Integration 的失败事件
* 可反向触发 Orchestration 的 `ReplanOnException`

---

## 4.8 Rating & Quotation BC

### 定位

面向你们“多 broker/多 carrier”的计价与报价：统一请求、规则加价、时效与限制校验、报价过期与再报价。

### 核心聚合

* `RateQuote`（聚合根）
* （可选）`RateCard`（你们自有产品价/加价规则）

### 关键命令

* `RequestRate`（向 Integration 下发）
* `CreateQuote` / `ExpireQuote` / `Requote`

### 关键事件

* `QuoteCreated/Expired`
* `RateSourceFailed`

### 依赖

* Integration BC：对接 broker/carrier rate API
* Product BC：产品约束与 SLA

---

## 4.9 Billing & Settlement BC

### 定位

将执行结果与计价结果转为应收/应付、账单与对账批次，支持差异处理与结算输出。

### 核心聚合

* `ChargeLine`、`Invoice`、`SettlementBatch`、`ReconciliationCase`

### 关键命令

* `GenerateCharges`（订阅 Shipment/Leg 完成）
* `IssueInvoice`
* `ReconcileCarrierBill`

### 关键事件

* `ChargesGenerated`
* `InvoiceIssued`
* `ReconciliationCompleted`

### 依赖

* 订阅 Shipment/Leg/Document 的完成/费用事件
* 与外部财务系统（ERP/Accounting）通过 ACL

---

## 4.10 Provider Management BC

### 定位

服务商与账号能力主数据：承运商、仓库、报关行、各自 endpoint、账号、能力、限制。

### 核心聚合

* `Provider`（聚合根）

  * `ProviderEndpoint`（同 Provider 多仓/多报关点）
  * `ProviderAccount`（与 Integration 的凭据引用）
  * `ProviderCapability`（可服务类型、覆盖、限制）

### 关键命令

* `RegisterProvider` / `UpdateProvider`
* `BindAccount` / `UpdateCapability`

### 关键事件

* `ProviderUpdated`
* `ProviderCapabilityChanged`

---

## 4.11 Network Planning BC

### 定位

网络节点与线路主数据：节点（仓/口岸/分拨/清关点）、线路（lane）、覆盖与时效，为 Orchestration 提供决策输入。

### 核心聚合

* `Node`、`Lane`、`Coverage`、`TransitTimeModel`（可选）

### 关键命令

* `PublishNetwork` / `UpdateLane` / `UpdateCoverage`

### 关键事件

* `NetworkPublished`
* `LaneUpdated`

---

## 4.12 Logistics Product BC

### 定位

你们对外卖的“线路产品/服务产品”抽象：包税/专线/特快/经济等，承载 SLA、限制、价格规则引用、可用网络约束。

### 核心聚合

* `LogisticsProduct`（聚合根）
* `ProductVersion`（版本化发布）
* `SLA` / `Constraint`

### 关键命令

* `CreateProduct` / `PublishProductVersion` / `DeprecateProduct`

### 关键事件

* `ProductPublished/Deprecated`

---

## 4.13 Integration BC（ACL）

### 定位

统一外部系统调用与回调：carrier/broker label/rate/tracking、仓库/WMS、报关系统。提供：

* 统一请求模型
* 统一错误映射 reason-codes
* 重试/限流/熔断/幂等
* 任务队列与回调处理

### 核心聚合/实体

* `Connector`、`ConnectorConfig`、`ExternalJob`、`ExternalCallLog`

### 关键命令

* `CreateExternalJob`
* `ExecuteExternalCall`
* `HandleCallback`

### 关键事件

* `ExternalJobSucceeded/Failed`（必须带 reason_code、retryable）

### 依赖

* Provider BC：账号/endpoint/能力
* Platform：密钥管理、审计、限流

---

## 4.14 Tenant & Configuration BC

### 定位

LOMS 作为 SaaS 的最小平台能力：租户上下文、配置项/开关、审计、国际化偏好、速率限制策略。

### 核心聚合

* `TenantPolicy`
* `FeatureFlag`
* `AuditLog`

### 关键命令/能力

* `SetTenantConfig`、`SetFeatureFlag`
* `AuditWriteOperation`（平台事件）

---

# 5. BC 间协作模型（事件/ACL/一致性）

## 5.1 事件优先（推荐）

* Shipment/Leg/Document/Integration 必须发布领域事件并进入 Outbox。
* Tracking/Exception/Billing 主要通过订阅事件构建自己的读模型或运营对象。

## 5.2 读写分离（CQRS）

* 写侧：严格走 command handler，维护聚合不变量。
* 读侧：可以独立读模型（表/视图/ES/OpenSearch）或按 BC 建 projection。

## 5.3 幂等与顺序

* 写 API：`X-Idempotency-Key` → `idempotency_record`
* 消费侧：`inbox_dedup` +（建议）`aggregate_version_gate`（按 shipment_id/leg_id 维护顺序门禁）
* 失败进入 `dlq_message`，允许 replay。

---

# 6. 状态机归属（谁负责什么状态）

* **FR 状态机**：FR BC（需求侧）
* **Shipment 状态机**：Shipment Execution BC（执行侧）
* **Leg 状态机**：Leg Execution BC（执行侧）
* **编排状态（计划版本、重规划过程）**：Orchestration BC（可选持久化）

contracts v1.0.0 中的 shipment/leg state machine 是强门禁；FR state machine 可以先内部定义，后续版本对外发布。

---

# 7. 数据边界与表归属（原则）

* 每个 BC 对其写模型（表）拥有所有权。
* 共享的技术表（Outbox/Inbox/DLQ/Idempotency/Audit）属于 Platform/Shared。
* FR↔Shipment 的映射表建议归属 FR BC（因为“需求到执行的分配关系”是需求侧事实），但 Shipment BC 可维护只读缓存以便快速查询。

---

# 8. 与 contracts v1.0.0 的对齐要求

## 8.1 必须对齐的合同资产

* reason-codes：服务端错误返回必须携带 `reason_code + retryable`
* state machines：command 前置条件 gate
* event routing matrix：event→topic 必须可确定
* event schema：envelope + event payload（建议强校验，至少 CI 校验）

## 8.2 建议新增合同资产（v1.1）

* FR 的 OpenAPI + FR 事件 schema
* i18n message catalog（zh-CN/en-US）纳入 contracts，并做 CI gate

---

# 9. 实施优先级与交付切片（建议一次性构建 BC 壳 + 分阶段填充）

## 9.1 P0（必须先稳定的“可运行闭环”）

1. FR BC（Create/Revise/Cancel + Allocation 结构）
2. Shipment BC（Create + Hold/Cancel + 状态机 gate）
3. Leg BC（Create/Assign/Dispatch + 状态机 gate）
4. Orchestration（FR→Shipment+Leg 的最小编排）
5. Integration（ExternalJob + 统一错误映射 reason-codes）
6. Outbox/Inbox/DLQ/Idempotency（平台机制）

## 9.2 P1（证据与运营增强）

* Document、Tracking、Exception

## 9.3 P2（商业闭环）

* Rating、Billing/Settlement

## 9.4 P3（网络与产品化）

* Provider、Network、Logistics Product

---

# 10. 团队协作与治理（必须写进仓库规则）

1. 禁止跨 BC 直接 import `domain`。
2. 所有对外 API 必须走 versioned router：`/v1`。
3. 所有写操作必须幂等：`X-Idempotency-Key`。
4. 所有领域事件必须进入 Outbox。
5. reason-code、state machine、event routing、schema 必须通过 CI 校验。
6. 任何新增命令必须补齐：前置条件、拒绝条件（reason-code）、事件与路由。

---

# 11. 交付物清单（本说明书对应的工程落盘）

当你要求我“按本说明书落盘工程”时，我将一次性输出：

* `app/bc/<bc_name>/{domain,application,interfaces,infra}` 目录树（15 个 BC 全部建好）
* `shared/platform`（auth/i18n/log/otel/metrics/health）
* `shared/contracts`（loader + gate）
* `shared/infra`（db/redis/outbox/inbox/dlq）
* 最小可运行用例：`CreateFR` → `Plan` → `CreateShipment+Leg` → `DispatchLeg`（Integration ExternalJob）
* DDL：FR、Allocation、Shipment、Leg、Outbox/Inbox/DLQ/Idempotency
* 多语言 message catalog（zh-CN/en-US）与 reason-codes 对齐校验

---

## 附：BC 名称建议（代码命名）

* `fulfillment_request`
* `shipment`
* `leg`
* `orchestration`
* `integration`
* `document`
* `tracking`
* `operations_issue`
* `rating`
* `billing`
* `provider`
* `network_planning`
* `logistics_product`
* `tenant_config`

---

如果你认可这版“完整 BC 设计说明书”，下一步你只需要回复一句：**“按此说明书落盘工程（v1.0.0）”**，我就会把它转换为一版可下载的完整 skeleton（一次性打包），并在其中把每个 BC 的边界、ports、事件与 contracts gate 以目录与占位代码固化下来。
