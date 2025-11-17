
# 为什么 Origo 合适

* 语义正中 PIM：本源/原点 → “单一事实源（SSOT）”的天然联想。
* 国际化发音顺：/ˈɔːrɪɡoʊ/（两拍），团队传播友好。
* 视觉母题明确：圆点/同心圆/经纬，延展性强。

# 风险与规避（两条就够）

* 同名较多：外部生态里可能与其他 “origo” 撞名；**内部使用 OK**。
* 技术冲突：PyPI/NPM/CLI 可能重名 → **包名/命令做轻度变体**即可。

# 工程命名（推荐）

* **仓库**：`origo-core`、`origo-schema`、`origo-content`、`origo-publish`、`origo-connectors`、`origo-admin`
* **Python 包名**：`origo_core` / `origo_schema` / `origo_publish` / `origo_connectors`
* **CLI**：`origoctl`（避免与潜在 `origo` 同名；命令更语义化）
* **环境变量前缀**：`ORIGO_`（如 `ORIGO_DB_URL`, `ORIGO_FEATURE_FLAGS`）
* **日志标签**：`product="origo"`, `service="schema|publish|admin"`

# 对外文案（内部文档/README 顶部占位）

* 标题：**Origo**
* 副标：**The source of product truth.**
* 一句话：将单一事实源拆解与治理，为每个渠道/语言生成准确可追溯的发布包。

# 视觉基线（足够启动设计）

* 母题：**原点 → 同心圆 → 经纬线**；避免雷同“地球仪”，主打几何极简。
* 主色：深墨蓝 `#0E1A2B`；强调：品绿 `#21B66E` / 琥珀 `#FFC24B`（少量）。
* 字体：标题 Sora/Inter（600），正文字体 Inter（400）。

# 快速落地清单

* [ ] 创建仓库：`origo-*` 六件套（core/schema/content/publish/connectors/admin）
* [ ] 包名与 CLI：`origo_*`、`origoctl` 写入 `pyproject.toml` 和 README
* [ ] 统一环境变量前缀 `ORIGO_` 与 `.env.example`
* [ ] 在 Bento 框架的 `runtime/composition.py` 中注册 Origo 的服务装配
* [ ] CI 复用你现有矩阵（3.11/3.12/3.13）

# 若以后需要对外或开源

* 首选对外名：**Origo**（保留），技术侧保持 `origoctl`/`origo_*`；
* 避免冲突的备用技术名：**`origo-hq`（组织）、`origo-core`（包）、`origoapp`（CLI 别名）**。

