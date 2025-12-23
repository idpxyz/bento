不冲突，但语义要分清楚：**shared/platform 是“能力库（library）”，runtime/ 是“应用装配（composition root / bootstrap）”。**
两者职责不同，所以我建议同时存在；你也可以把 runtime/ 放进 shared/platform，但那会把“库”与“应用入口”混在一起，后期多进程/多入口（API、worker、replayer）会变脏。

---

## 1) 两者的职责边界

### shared/platform：可复用的“基础能力包”

放这里的东西应该满足：**任何 BC、任何进程、任何服务都可以拿来复用**，且不依赖具体业务模块注册顺序。

典型内容：

* config primitives（Settings 结构、env loader、secret resolver 的通用实现）
* logging/metrics/tracing（OpenTelemetry 初始化工具、log formatter、correlation/causation id 中间件）
* auth/i18n/time/money 等通用值对象或中间件
* runtime primitives（例如：`Module` 接口、`Registry` 抽象、`Container` 抽象、`Gate` 抽象）
* “可插拔适配器”的接口定义（EventBusPort、Clock、IdGenerator 等）

一句话：**平台能力与抽象**。

---

### src/loms/runtime：项目级“装配根”（composition root）

放这里的东西应该满足：**只服务 LOMS 这个可执行单元**，负责把平台能力 + 各 contexts 的模块拼起来，并给不同进程入口复用。

典型内容：

* module registry 的“实例化与注册清单”（哪些 modules 启用、顺序、依赖图）
* config wiring（把 env 配置映射到各模块 settings、给模块注入具体 adapter）
* infra wiring（选择 postgres 实现、pulsar 实现、outbox worker 实现等）
* gates 启动（启动时 contract 校验、schema 校验、migration check）
* 多入口 bootstraps：

  * `runtime/api_app.py`（FastAPI app 构建）
  * `runtime/worker_outbox.py`
  * `runtime/worker_inbox.py`
  * `runtime/replay_job.py`

一句话：**把“能用的积木”拼成“能跑的系统”**。

---

## 2) 为什么不建议全部塞进 shared/platform

如果把“装配根”也放进 shared/platform，会出现三个工程后果：

1. **库与应用耦合**
   platform 原本可给别的系统复用（未来 Prism/Origo/Gatekeeper），但装配根包含 LOMS 的具体模块清单、topic 命名、db 连接选择，这些都不应成为“平台库”的依赖。

2. **多入口会混乱**
   LOMS 至少有 API + workers（outbox/inbox/dlq/replay）。装配代码会迅速长大。放平台库里会导致平台层出现大量“应用特定 if/else”。

3. **测试与演进困难**
   composition root 常常需要在集成测试里替换 adapter（in-memory bus、sqlite、fake provider）。如果它在 platform 内，测试替换路径会变复杂且更容易破坏其它系统。

---

## 3) 你如果坚持“只要一个地方”，也可以怎么做（但要有规则）

### 方案 A（推荐）：两层结构（我之前建议的）

* `shared/platform`：抽象与能力
* `runtime/`：装配与入口

最清晰、最符合六边形和可商业化交付的工程实践。

### 方案 B：只保留 shared/platform，把 runtime 融进去

可以，但要强约束：

* `shared/platform/runtime_primitives/*`：抽象、接口、工具函数
* `src/loms/bootstrap/*`：装配根（仍然不叫 shared/platform）
  也就是说，**你可以改名，但“库/装配”仍要分目录**。

---

## 4) 一个可执行的命名与落点建议（避免争议）

* `src/loms/shared/platform/`：只放 primitives（不可导入任何 contexts）
* `src/loms/runtime/`：只放装配（允许导入 contexts 与 shared）
* 规则：contexts 不允许 import runtime；runtime 可以 import contexts

这条依赖方向规则一旦立住，你们的结构会长期保持“科学”。

如果你愿意，我可以基于你当前目录，直接给出一份“依赖规则 + lint/gate 检查点清单”（例如用 ruff/pyproject 约束 import 层级），保证团队不会把边界写坏。
