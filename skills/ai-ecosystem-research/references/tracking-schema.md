# 持续研究记录

每期新任务目录：`research/runs/YYYY-MM-DD/<mode>-<topic-slug>/`（例如 weekly-global、monthly-global、deep-dive-memory）。同日同主题新运行追加 -02 等唯一后缀；排版修订保留原任务并记录修订。兼容既有日期目录，不迁移或覆盖历史。每期保存 run.json：run_id、mode、topic、timezone、window_start、window_end、cutoff、created_at、revision_at、language、audience、output_format。专题 window_start 可为 null；月报注明 calendar_month 或 rolling_30_days。每期目录建议包含 `report.md`、`evidence.json`、`candidates.json`、`coverage.md`、`acceptance.md`。需要榜单的任务另存 `rankings.md`；专题不强制创建空榜单。共享 `research/projects.json`、`research/predictions.json`；指标快照按日期单独保存。先阅读既有记录，追加本期状态，不抹掉历史。

## 证据

`id, entity_id, claim, url, title, publisher, published_at, event_at, retrieved_at, date_precision, source_timezone, evidence_type, access_status, limitations`

日期未知为 null；retrieved_at 可精确到日期但必须说明 precision，不能伪造时分秒。claim 是简短释义，性能主张注明归属。相同 URL 可有多条主张，但不算独立来源。

## 候选

`id, name, category, discovered_via, event_type, event_date, evidence_ids, decision, reason, next_check`

decision 为 selected／watch／deferred／excluded；有可读原始来源才升级核心事实。event_type 为 initial_release／weights_release／update／discussion／paper／unknown。

## 项目

`id, name, canonical_url, aliases, first_seen, first_release, status, evidence_ids, history, next_check`

history 追加日期、变化、证据，不覆盖。模型、工具、论文同名时使用发布者／仓库／论文 ID 区分；报告内跨社区同一项目去重。

## 指标快照

`entity_id, platform, metric, value, unit, metric_window, observed_at, source_url, cache_status, scope, limitations`

未知 value 用 null；平台显示近似值保留原显示，不伪造精确整数。首次只有一条快照，不计算增量。过期缓存不写成实时基线。

## 判断与预测

`id, statement, created_at, evidence_ids, confidence_reason, scope, observable_signal, falsifier, due_date, status, history`

status 为 open／supported／weakened／refuted／inconclusive。到期无新证据是 inconclusive，不是 supported。回访按信号判断，不追改过去的预测内容。

## 验收

月报另存 `review.json`，将回访集合与逐项判定落盘：

以 review.json 作为规范集合索引；可引用分开的项目／预测明细，但索引必须解析到这些文件。不能只在正文写“全部回访”而无集合、条目和状态可核对。集合规模从本次基线推导，不固定为某期数量。

`entity_id, prediction_id, review_kind, inclusion_reason, baseline_at, baseline_version, baseline_evidence_ids, prior_statement, current_at, current_version, current_evidence_ids, comparability, observed_change, verdict, reasoning, decision_implication, next_check, review_status`

prediction_id 可为 null（非预测项目回访）；review_kind 为 prediction／project／new_baseline。verdict 沿用 supported／weakened／refuted／inconclusive，尚未到期且证据不足可为 open。新纳入项目无旧判断时 prior_statement、baseline_at、verdict 为 null，review_kind 为 new_baseline，不能强行裁定历史判断。review_status 使用 reviewed／pending／excluded，排除说明理由。文件包含集合形成规则、到期判断总数及已回访数；只对明确定义的集合计算覆盖率，不外推全球生态。

周报把候选与待验证假设写入现有 candidates／predictions；月报引用原记录并在 history 追加本次证据、判定与修订内容，原 statement、created_at、原期限不可追改。修订后的新预测用新 id 和 supersedes 指向旧预测。历史文件不覆盖。

逐项记录 requirement、status（pass／partial／fail）、evidence、limitation、remedy。机械检查只证明结构、引用一致性；事实复核、叙事质量和覆盖程度必须另审。最终签收说明哪些工作完整、哪些输出受来源／执行条件限制。

回访补充 change_kind（事实纠错／补充遗漏／收窄／细化／证据强度变化／维持）、evidence_temporality（登记前历史／登记后事件／当前快照／未知）；混合证据逐条记录。区分预测生命周期 status 与本次证据 verdict：未到期且条件未满足继续 open；确有证据提前满足成立或推翻条件时说明依据与判定时间，不因未到期忽略决定性证据。无到期或可判定样本时不输出命中率；输出时定义样本、分母与未定项处理。

每条主张绑定具体 evidence_id 与 run_id／相对证据路径，跨期 ID 不得含糊。证据台账保存简短主张、归属和时间，不用含多个引文的整段正文替代逐条映射。追加前保留可比原记录，写后核对原句、日期、期限与信号未被改写；按 run_id＋对象 ID＋修订号去重，重复执行不得重复追加历史。研究数据、采集摘录和某期验收脚本留在研究目录，不复制进 skill 安装目录。
