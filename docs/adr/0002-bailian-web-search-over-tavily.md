# ADR-0002 选择 Bailian DashScope web_search 作为检索工具

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Architecture Team

## Context

Researcher 节点需要外部搜索引擎获取实时网页内容，是 deep-research 报告引用的主要来源。候选厂商必须同时满足：
1. **中文检索质量** — 项目含 1/3 中文问题，英文厂商对中文站点覆盖差；
2. **国内合规** — 报告内容合规审计可过；
3. **与阿里栈集成** — 后端模型、向量库、对象存储均在阿里云；
4. **按调用计费、可观测** — 单次 0.01–0.05 元级别，能挂 Langfuse tokens 维度。

## Decision

采用 **DashScope SDK 1.27.7** 的 `web_search` 标准版（`search_type=web`，`count=10`），通过 `langchain_classic.tools.BailianWebSearch` 包装成 LangGraph 节点可用的 Tool。返回值自带 `title` / `url` / `snippet` / `content`，覆盖 fetch-page 后的二级再抓取需求。

## Alternatives

| 方案 | 取舍 |
| --- | --- |
| **Tavily** | 英文检索一流，但中文结果数量低且价格高（$0.005/call）；国内访问偶发延迟。 |
| **Serper (Google Serp)** | 数据质量好，但合规审批需走 Google API，不符合 v1 国内合规口径。 |
| **Bing Web Search API** | 国内版需企业资质；中文结果偏向国际市场。 |
| **Bailian web_search（采纳）** | 见 Decision。 |

## Consequences

**正面**
- 与 Qwen3-Max 同账号计费，账单合并，预算管控简单。
- 检索结果含 `published_at` 字段，方便 Researcher 节点过滤时间敏感问题。
- SDK 内置 retry / backoff；自研 fetch-page 失败时可改切 `count=20` 一次性抓够。

**负面**
- 域名白名单受限：少数海外学术站点（arxiv.org）需经企业版开通。短期通过把 arxiv 当作 `fetch_page` 直连兜底。
- 速率限制 20 QPS；并发 ≥ 8 时 Researcher 节点要做 token bucket。

**回退成本**

切到 Tavily 仅需替换 Tool 包装层（约 2 人天），但要重做中文问题回归。
