# 评估设计（Eval）

本文档定义 deep-research v3 的离线评估管线：数据集来源、ground truth 结构、LLM-as-judge 评分规则、e2e 触发方式与 Langfuse Datasets 落地。v1 不做线上 A/B，所有质量门禁来自 nightly 跑批。

## 1. 数据集组成

| 来源 | 数量 | 筛选标准 |
| --- | --- | --- |
| HotpotQA `distractor` 训练集 | 100 题 | 含 `supporting_facts` 与 `answer` 的 multi-hop 题 |
| 自造业务题 | 5 题 | 覆盖中文检索 / 时间敏感 / 多跳推理三类典型问题 |

总数 105 题，单独配额 `infra/eval/datasets/v1.jsonl`，CRLF 结尾、每行一题。

导入方式：

```bash
# 1) 下载 HotpotQA distractor
wget https://hotpotqa.s3-us-west-2.amazonaws.com/en-distractor.jsonl -O hotpotqa.jsonl

# 2) 抽样 100 题 + 自造 5 题拼装
python scripts/eval/build_dataset.py \
    --hotpotqa hotpotqa.jsonl \
    --custom ./custom.jsonl \
    --out infra/eval/datasets/v1.jsonl

# 3) 推送至 Langfuse Datasets
python scripts/eval/push_to_langfuse.py --dataset deep-research-v1 \
    --file infra/eval/datasets/v1.jsonl
```

## 2. Ground Truth 字段

每个 item 含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | HotpotQA 用原 `id`，自造题用 `custom-{n}` |
| `question` | string | 原始问题 |
| `reference_answer` | string | 标准答案（黄金短答） |
| `reference_sources` | string[] | 用于支撑事实的 Wikipedia / 网页 URL |
| `key_facts` | string[] | 报告中必须出现的事实点，用于 coverage 计算 |
| `difficulty` | enum | `easy` / `medium` / `hard` |
| `language` | enum | `en` / `zh`，用于分层统计 |

`key_facts` 由人工标注，是 `score.coverage` 的对标基准。

## 3. LLM-as-judge Prompt 模板

Judge 模型选 **o3-mini**（强推理、低成本），与 critic 节点同源以保证口径一致。模板存于 `infra/eval/judge/prompts/v1.yaml`：

```yaml
system: |
  你是 deep-research 评估员。对比 [QUESTION] / [REPORT] / [REFERENCE] /
  [KEY_FACTS]，按三项 0–1 打分，并给出 1 句理由。

user: |
  QUESTION: {{question}}
  REFERENCE_ANSWER: {{reference_answer}}
  KEY_FACTS: {{key_facts | join(", ")}}

  REPORT:
  {{report}}

  请返回 JSON：
  {
    "factual_accuracy": <0-1>,   # REPORT 事实与 REFERENCE 一致程度
    "citation_density":   <0-1>, # REPORT 引用条数 / 含 URL 句子数
    "coverage":          <0-1>, # KEY_FACTS 中出现在 REPORT 的比例
    "reason":            "<一句理由>"
  }
```

## 4. Score 维度计算公式

| 维度 | 公式 | 来源 |
| --- | --- | --- |
| `factual_accuracy` | judge 直接给出 | judge |
| `citation_density` | judge 直接给出 | judge |
| `coverage` | judge 直接给出 | judge |
| `latency` | trace `score.latency` 字段 | OTel |
| `token_cost` | trace `score.token_cost` 字段 | callback |
| `tool_failure_rate` | trace 字段 | Researcher |

`factual_accuracy` 与 `coverage` 的最终值取 `judge_score` 与 `human_review`（首轮 5 题抽样人工复核）的均值；后者只在发版前跑一次。

## 5. e2e 触发

| 触发方式 | 时间 | 预算上限 | 用途 |
| --- | --- | --- | --- |
| Nightly cron | 每日 02:00 (Asia/Shanghai) | $5 USD | 监控日常回归 |
| PR-CI 触发 | PR 标题含 `eval` | $5 USD | 改 prompt / 路由时手动触发 |
| 发版前 | `tag` push 时 | $10 USD | 灰度前最后门禁 |

脚本入口：`python scripts/eval/run_e2e.py --dataset deep-research-v1 --concurrency 4`。

预算护栏在脚本前段检查 Langfuse 当日累计 cost，超过阈值直接 fail-fast，避免跑废。

## 6. Langfuse Datasets 用法

Langfuse v4 Datasets 支持 **Experiment Run** 模式：

```python
from langfuse import get_client
langfuse = get_client()

for item in dataset.items:
    trace = langfuse.get_current_trace_id()
    result = run_pipeline(item.question)         # 调真实 graph
    langfuse.score_current_observation(
        name="factual_accuracy", value=judge(item, result),
        trace_id=trace,
    )
langfflush_dataset_run(dataset_name="deep-research-v1", run_name="nightly-2026-10-15")
```

每次跑批在 Langfuse UI 留一组 trace，可按 `score.factual_accuracy` 分布对比前回退结果。

## 7. 落地清单

- [x] `infra/eval/datasets/v1.jsonl` 105 题
- [x] `scripts/eval/build_dataset.py` / `run_e2e.py` / `push_to_langfuse.py`
- [x] cron `0 2 * * * python scripts/eval/run_e2e.py` 经 K8s CronJob
- [x] 数据集版本进入 Git LFS，避免污染主分支
- [x] 跑批结果日报推送 Lark 群
