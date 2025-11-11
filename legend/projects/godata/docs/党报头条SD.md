《**使用 Wagtail CMS 构建“今日头条级”个性化新闻平台——系统设计书**》。
定位：**Wagtail 负责内容治理（CMS）**，前台与个性化能力采用**Headless 架构**。

---

## 0. 目标与范围

**业务目标**

* 面向多品牌/多站点（可演进至多租户），支持频道、专题、活动页、聚合 Portal。
* “今日头条级”个性化：**秒级生效**、**强个性化**、**去重与多样化**、**编辑共治**（置顶/必显/禁显）。
* 全链路可观测与 A/B 实验。

**关键非功能指标（SLO）**

* **首屏 TTFB p95 ≤ 800ms**（命中边缘缓存/ISR）。
* **Feed/Slate 接口 p95 ≤ 150ms**（召回≤60ms + 重排≤60ms + 组板≤30ms）。
* **发稿→全量曝光 ≤ 5–10 秒**（事件→索引→缓存精准失效）。

---

## 1. 总体架构

```text
用户 ←→ CDN/边缘中间件 ←→ 前台渲染层（Next.js SSR/ISR 或 Wagtail SSR）
                         ↘
                          个性化组板（Slate Service, FastAPI/ASGI）
                           ↙        ↘
                 特征服务/画像       搜索服务（ES/OpenSearch）
                        ↑               ↑
                   行为日志(曝光/点击/停留/负反馈)/趋势/聚类（Flink/Spark/Celery）
                                 ↑
                         事件总线（Kafka/PubSub）
                                 ↑
                      Wagtail CMS（工作流/发布/审核/预览/图片Renditions）
```

**职责分离**

* **Wagtail CMS**：内容模型、工作流、发布、预览、事件、精准失效、素材与 Rendition。
* **Slate Service**：多路召回、重排打分（ERT 目标）、受限最优化（配额/多样化/去重/编辑规则）。
* **前台（Next.js）**：SSR/ISR、边缘缓存与轻量个性化、契约化页面装配（Layout-as-Data）。
* **离线/近线**：同题聚类、趋势、索引刷新、画像更新、质量/安全评分。
* **搜索**：ES/OpenSearch，支持 story\_cluster\_id/query rewrite/推荐召回候选。

---

## 2. 内容域建模（Wagtail）

### 2.1 主要模型

* `ArticlePage(Page)`：文章（标题、副题、正文块、媒体、标签、来源、topic、story\_cluster\_id、auth\_score、safety\_flags、publish\_at、seo/open-graph）。
* `ChannelPage(Page)`：频道（规则/过滤/模板/默认排序、频道主题包 ThemePack）。
* `ThemePack(Snippet)`：**设计令牌**（colors/radius/spacing/fonts/shadow…），支持租户/站点/频道覆盖。
* `AudienceSegment(Snippet)`：人群细分（geo/设备/兴趣/实验桶）。
* `EditorialRule(Snippet)`：置顶、必显、禁显、权重修正（作用域：频道/站点；期限；优先级）。
* `Media/Image/Document`：Wagtail 原生+Rendition（派生尺寸/裁剪/格式）。

**ArticlePage 示例（节选）**

```python
# apps/news/models/pages.py
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.api import APIField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from .blocks import BodyStream  # 富文本/图集/嵌入等
from .snippets import ThemePack, AudienceSegment

class ArticlePage(Page):
    subtitle = models.CharField(max_length=200, blank=True)
    body = StreamField(BodyStream, use_json_field=True)
    source_id = models.CharField(max_length=64, db_index=True)
    topic_id = models.CharField(max_length=64, db_index=True, blank=True)
    story_cluster_id = models.CharField(max_length=64, db_index=True, blank=True)
    auth_score = models.FloatField(default=0)         # 来源权威度
    safety_flags = models.JSONField(default=dict)     # 低俗/涉政/侵权等
    published_at = models.DateTimeField(null=True, db_index=True)

    api_fields = [
        APIField("title"), APIField("subtitle"), APIField("body"),
        APIField("source_id"), APIField("topic_id"),
        APIField("story_cluster_id"), APIField("auth_score"),
        APIField("safety_flags"), APIField("published_at"),
        # Image renditions 在 Serializer 中返回绝对 URL + 变体
    ]

    content_panels = Page.content_panels + [
        FieldPanel("subtitle"),
        FieldPanel("source_id"),
        FieldPanel("topic_id"),
        FieldPanel("story_cluster_id"),
        FieldPanel("auth_score"),
        FieldPanel("safety_flags"),
        FieldPanel("published_at"),
        FieldPanel("body"),
    ]
```

### 2.2 发布与事件（秒级生效）

```python
# apps/news/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models.pages import ArticlePage
from .events import publish_event, purge_related_cache

@receiver(post_save, sender=ArticlePage)
def on_article_saved(sender, instance: ArticlePage, created, **kwargs):
    if instance.live:  # 发布态
        publish_event("ArticlePublished", {
            "id": instance.id,
            "story_cluster_id": instance.story_cluster_id,
            "channel_ids": instance.get_parent().id,  # 简化
            "published_at": instance.published_at.isoformat(),
            "source_id": instance.source_id,
            "auth_score": instance.auth_score,
            "safety_flags": instance.safety_flags,
        })
        purge_related_cache(instance)  # 精准失效（页面自身 + 相关频道/聚合位）
```

**事件 → 近线任务**

* 触发 **ES/OpenSearch 索引**更新（主索引与排序字段）。
* 刷新**召回候选集合**（Redis/ES）。
* 驱动 **ISR On-demand revalidate** 或 CDN Purge。

---

## 3. 前台渲染与页面装配（Headless 推荐）

### 3.1 Layout-as-Data（页面与区块契约）

由 CMS 输出**页面契约**，前端依据契约请求各个 slot 的 slate：

```json
{
  "tenant": "news-a",
  "page": "home",
  "version": "2025-08-05T00:00:00Z",
  "slots": [
    {"id":"top_lead","type":"story","N":1, "constraints":{"must_new":true, "per_source":1}},
    {"id":"headline","type":"list","N":6, "constraints":{"per_source":2,"per_category":3}},
    {"id":"trending","type":"list","N":5, "constraints":{"time_window":"6h"}},
    {"id":"ad_5","type":"ad","pos":5}
  ]
}
```

**Next.js 关键点**

* `ISR`（如 `revalidate: 60~300s`）+ **On-demand Revalidate**（CMS 发布回调）。
* **边缘中间件**：基于 `Geo/Device/AB 桶` 选择轻量变体，不打碎主缓存。
* 主题：从 CMS 的 `ThemePack.tokens` 注入 CSS 变量，驱动 Tailwind + shadcn/ui。

### 3.2 预览闭环（草稿态）

* Wagtail “预览”→ 生成带签名 URL → 前端 `api/preview` 开启 **Preview Mode** → 拉取草稿数据渲染（禁缓存）。

---

## 4. 个性化组板（Slate Service）

### 4.1 接口契约（OpenAPI 摘要）

```
POST /v1/slate/build
Req: { user_ctx, page_contract, recent_impressions }
Res: { slots: [{id, items: [{article_id, view_variant, reason, ttl}...]}] }
```

**user\_ctx**

* `uid`（可匿名设备 ID）、`geo`、`device`、`segments`（兴趣/标签）、`ab_bucket`、`recent_impressions`。

**page\_contract**

* 来自 CMS 的 slot 契约：每个 slot 的 `N`、配额、必新/必深、广告位定义、编辑置顶/禁显。

### 4.2 在线流程与时延预算

1. **多路召回（≤60ms）**

   * 热门趋势、相似内容（向量/协同）、地理/频道召回、编辑精选、探索桶；
   * **硬过滤**：安全/拉黑/重复曝光/禁显/低权威。
2. **重排打分（≤60ms）**

   * 目标：**ERT（有效阅读时长）** 最大化，次目标 CTR/互动；
   * 特征：短期会话、长期画像、内容嵌入、质量/安全/权威、上下文（时段/设备/地理）。
3. **受限最优化组板（≤30ms）**

   * 约束：`per_source`、`per_category`、`min_fresh`、`cluster 去重`、`ad_slots`、`编辑置顶`。
   * 算法：**贪心 + 约束检查 + MMR 多样化**（必要时 DPP/ILP）。

**伪代码（节选）**

```python
def build_slate(candidates, N, quotas, pinned):
    slate = list(filter(safe_and_dedup, pinned))
    state = init_quotas(quotas, slate)
    for item in sorted(candidates, key=score, reverse=True):
        if violates(item, state): continue
        if is_duplicate_cluster(item, slate): continue
        slate.append(item); update(state, item)
        if len(slate) == N: break
    return mmr_diversify(slate, alpha=0.7)
```

---

## 5. 搜索与同题聚类

**搜索（ES/OpenSearch）**

* 索引映射：`title/abstract/body`（中文分词）、`topic_id`、`story_cluster_id`、`source_tier`、`auth_score`、`publish_at`、`doc_type`。
* 排序：时间衰减 + 质量/权威 + 个性化相关性。

**同题聚类**

* 离线：**SimHash + 句向量（e5/SGPT）** + LSH/层次聚类 → 产出 `story_cluster_id`。
* 增量：新稿与近窗对比，阈值命中加入 cluster 或开新 cluster。
* 在线去重：同 `story_cluster_id` 一屏仅一条，取质量/新鲜度更优者。

---

## 6. 缓存与精准失效

**缓存层次**

* **CDN/边缘**：HTML/JSON，`stale-while-revalidate`；变体以 Geo/Device/AB 为限。
* **ISR/页面缓存**：Key 例 `site:{id}:page:{name}:ver:{hash}:geo:{r}:device:{d}`。
* **片段缓存**：频道块、文章卡片（Key 含分页/筛选）。
* **Slate 级缓存**：slot 请求可缓存 10–60s（受编辑置顶影响时缩短）。
* **数据缓存**：召回候选短缓存（Redis 10–20s），重排特征读本地/Redis。

**精准失效拓扑**

* Article 发布/撤稿 → 计算受影响 **channel/slot** →

  1. CDN Purge 精确路径；
  2. 触发 ISR `revalidateTag`（Next.js）；
  3. 删除 Redis 片段与候选 Key（含 cluster、channel）。

---

## 7. 安全与可信

* **安全评分**：NLP 分类（涉政/低俗/歧视）、规则库（敏感词/黑名单来源）、版权标识；生成 `safety_flags/safety_score`，高风险**拦截+人审**，中风险降权。
* **权威优先**：突发模式下提升 `auth_score` 权重。
* **指标护栏**：当 CTR↑ 但 **ERT/完读率** 下降，自动降权或回滚策略。

---

## 8. A/B 实验与冷启动

* **分桶**：设备/用户稳定哈希；变体配置进入 Slate 规则（不同 λ、配额、探索率）。
* **关键指标**：ERT、完读率、7/30 日留存、负反馈率、来源/类目覆盖度。
* **冷启动**：新用户以频道热点+权威+轻量探索（ε=0.05）；新内容以多臂老虎机小流量探测，设 bad-case 保护阈值。

---

## 9. 观测与告警

* **APM/Tracing**：Sentry/Elastic APM；链路：前台 → Slate → ES/Redis → CMS API。
* **Metrics**：Prometheus/Grafana

  * Slate：召回/重排/组板时延、命中率、降级次数；
  * 缓存：CDN/ISR/Redis 命中率；
  * 页面：TTFB/LCP/INP；
  * 业务：ERT、完读率、负反馈。
* **告警**：接口 p95 超阈、缓存命中骤降、负反馈激增。

---

## 10. 多站点/多租户与权限

* **多站点**：Wagtail Sites 管多个树；站点级主题/域名/媒体域名；API 按站点隔离。
* **多租户（演进）**：租户隔离数据库/索引/缓存命名空间；主题与组件库复用。
* **鉴权集成**：如 Logto/Auth0（SSO/RBAC），用于后台和 Portal 登录；内容接口区分匿名/登录态，登录态可扩展个性化范围。

---

## 11. 部署与容量规划

* **Wagtail CMS**：2–3 副本 / 4–8 vCPU；读写分离（PostgreSQL 主从）；静态/媒体走对象存储+CDN。
* **Slate Service**：按 RPS 水平扩容（无状态）；1 核≈ 150–300 RPS（取决于特征/ES 时延）。
* **ES/OpenSearch**：3 主 + 若干热节点；写入（发布峰）与查询（阅读峰）分角色。
* **Redis**：主从 + 哨兵；区分**片段缓存**与**特征缓存**命名空间。
* **CDN**：全局边缘，支持 `stale-while-revalidate`、精准 Purge API。
* **容灾**：跨可用区部署；主从切换/降级策略（Slate 超时→回退频道热点）。

---

## 12. 开发与 CI/CD

* **Monorepo**：`apps/{cms-wagtail,web-portal,slate-service,rec-workers}` + `packages/{contracts,ui,tokens,cms-sdk}`。
* **Contracts 先行**：OpenAPI/JSONSchema/Avro 在 `packages/contracts`，前后端对齐。
* **流水线**：lint/test/build/镜像/集群部署（Blue-Green/Canary），策略变更优先灰度。
* **预生产**：影子流量验证 Slate 策略，指标合格再提升权重。

---

## 13. 迁移路线（从单站到头条级）

1. **MVP**：Wagtail SSR + Tailwind，频道/文章/专题上线；建立 `api_fields` 与事件。
2. **Headless 前台**：Next.js + ISR + 主题令牌接入；CMS→前台预览打通。
3. **Slate v1**：规则召回 + 贪心组板 + 去重/配额；ES 索引连通。
4. **Slate v2**：ERT 重排 + MMR 多样化 + 编辑共治；A/B 框架与护栏。
5. **近线**：聚类与趋势计算；个性化分片边缘化；完善观测与告警。

---

## 14. 附录：关键契约样例

### 14.1 Slate Build 请求（节选）

```json
{
  "user_ctx": {
    "uid": "anon:3c9f...",
    "geo": "US-AZ",
    "device": "mobile",
    "segments": ["sports_fan", "tech_viewer"],
    "ab_bucket": "B"
  },
  "page_contract": {
    "tenant": "news-a",
    "page": "home",
    "slots": [
      {"id":"top_lead","type":"story","N":1,"constraints":{"must_new":true}},
      {"id":"headline","type":"list","N":6,"constraints":{"per_source":2,"per_category":3}}
    ],
    "pinned": [{"slot":"headline","article_id":"A123","priority":1}]
  },
  "recent_impressions": ["A001","A002","A003"]
}
```

### 14.2 Slate Build 响应（节选）

```json
{
  "slots": [
    {
      "id": "headline",
      "items": [
        {"article_id":"A123","view_variant":"card-lg","reason":"pinned","ttl":120},
        {"article_id":"A456","view_variant":"card-sm","reason":"fresh+relevance","ttl":60}
      ]
    }
  ]
}
```

### 14.3 缓存 Key 规范（示例）

```
page: site:{id}:page:{name}:ver:{hash}:geo:{r}:dev:{d}
frag: site:{id}:frag:{channel}:{page}:{qhash}
slate: site:{id}:slot:{slot_id}:ab:{bucket}:geo:{r}:dev:{d}
cand: recall:{channel}:{window}:{hash}
```

---

## 15. 代码骨架（最小可运行片段）

**（1）Wagtail → Kafka 事件 & Purge**

```python
# apps/news/events.py
import requests, json, os

def publish_event(topic, payload):
    # 简化：HTTP 网关转 Kafka
    requests.post(os.environ["EVENT_GATEWAY"], json={"topic": topic, "payload": payload})

def purge_related_cache(article):
    # 失效路径：文章详情 + 相关频道/首页 slot
    paths = [f"/article/{article.id}", "/", f"/channel/{article.get_parent().slug}"]
    for p in paths:
        requests.post(os.environ["CDN_PURGE_API"], json={"path": p})
    # 触发 ISR
    requests.post(os.environ["ISR_REVALIDATE_API"], json={"tags": ["home","channel:"+article.get_parent().slug]})
```

**（2）Next.js 预览 Route（节选）**

```ts
// app/api/preview/route.ts
import { draftById } from "@/lib/cms";
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id"); const token = searchParams.get("token");
  // 校验 token …
  // @ts-ignore
  return new Response(null, { status: 307, headers: { "Location": `/preview/${id}` }});
}
```

**（3）Slate Service 路由（FastAPI）**

```python
# apps/slate-service/src/api/v1.py
from fastapi import APIRouter
from .core import recall, rank, slate

router = APIRouter()

@router.post("/slate/build")
def build(req: BuildRequest) -> BuildResponse:
    candidates = recall.multi(req)
    ranked = rank.score(candidates, req.user_ctx)
    slots = slate.assemble(ranked, req.page_contract)
    return BuildResponse(slots=slots)
```

---

## 16. 风险与对策

| 风险        | 表现           | 对策                                               |
| --------- | ------------ | ------------------------------------------------ |
| Purge 风暴  | 发布频繁导致首页全失效  | 精准失效（按 slot/cluster），启用 `stale-while-revalidate` |
| 个性化打碎缓存   | 变体过多命中率下降    | 仅 Geo/Device/AB 做边缘变体；用户级个性化异步加载                 |
| 重排过拟合 CTR | ERT/完读率下降    | 多目标优化，护栏触发自动回滚                                   |
| ES 延迟波动   | Slate p95 抬升 | 本地/Redis 热候选兜底；超时降级频道热点                          |
| 聚类误伤      | 高频事件被过度去重    | 低阈场景允许多代表卡；编辑白名单优先                               |

---

## 17. 实施计划（8 周参考）

* **W1–W2**：Wagtail 模型/事件/主题包，Next.js 基座 + 预览；ES/Redis/Kafka 基础。
* **W3–W4**：Layout 契约与装配、Slate v1（规则召回+贪心组板）、缓存与 Purge。
* **W5–W6**：Slate v2（ERT 重排+MMR 多样化+编辑规则）、近线聚类/趋势。
* **W7–W8**：A/B 与护栏、观测与告警、容量压测与灰度、故障演练与Runbook。

---

### 结语

这套设计以 **Wagtail 做强内容治理**，同时用**能力分层**满足“头条级”个性化与时效诉求；可从单站点快速起步，平滑演进到多租户与 Portal。
如果你确认 **云环境（AWS/GCP/Azure/自建）** 与 **语言偏好（Python/Go/Node）**，我可以把上述各模块的**可运行样例仓库骨架**与 **CI/CD 脚本**发给你，并细化 **ES Mapping、召回 Query DSL、重排特征列与训练样例**，帮助你在 4–8 周内上线第一版。
