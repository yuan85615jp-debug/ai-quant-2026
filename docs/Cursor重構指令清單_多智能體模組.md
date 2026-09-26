# Cursor 重構指令清單 —— 多智能体交易员模组

> 使用方式：在 Cursor 中打开 `ai_quant_2026` 项目，按顺序把下方指令复制粘贴到 Chat / Composer 中执行。  
> 每条指令执行完并确认结果后再进行下一条。

---

## 指令 1：理解现有代码结构

```
请完整阅读 multi_agent_traders/ 目录下的所有文件，包括：
- models.py
- agents/ 下的所有文件
- prompts/ 下的所有文件
- decision_maker.py
- data_provider.py
- main.py
- config.yaml

然后用简洁的中文总结：
1. 整体架构与数据流
2. 每个交易员的角色差异
3. 目前还缺少哪些生产级能力（例如真实数据源、回测、评估、日志持久化等）
```

---

## 指令 2：替换为真实数据源（示例：东方财富或新浪）

```
请修改 data_provider.py，新增一个函数 get_realtime_market_data(stock_code: str) -> MarketData。

要求：
1. 使用 requests 从公开接口获取该股票最近 120 个交易日的日线数据（优先东方财富或新浪，注意处理编码与反爬）
2. 使用 pandas + pandas_ta（或简易计算）计算 MA5/10/20/60、MACD、RSI、KDJ、布林带、量比等
3. 取最新一行转换为 MarketData 并返回
4. 加入基本的重试与异常处理
5. 保持 get_demo_market_data 不变，作为 fallback
6. 不要破坏现有接口签名
```

---

## 指令 3：增加决策结果持久化

```
请在 multi_agent_traders/ 下新增 result_store.py，实现简单的结果存储：

1. 每次 DecisionMaker.run() 完成后，把完整的 FinalDecision（含各交易员意见）以 JSON 文件形式保存到 outputs/ 目录
2. 文件名格式：{stock_code}_{timestamp}.json
3. 同时追加一行到 outputs/decisions.csv（便于后续统计分析）
4. 在 main.py 中调用这个存储逻辑
5. 使用 pathlib，注意创建目录
```

---

## 指令 4：优化提示词（加入更多上下文）

```
请阅读 prompts/ 下的四个提示词文件。

针对机构交易员（institutional.py），请增强 System Prompt，额外要求模型输出：
- 预估冲击成本（基点）
- 建议建仓天数
- 日内成交占比上限

同时更新 models.py 中的 TraderOpinion，增加对应可选字段（impact_cost_bps, build_days, max_intraday_volume_pct），并确保 BaseTrader 能正确解析这些新字段（解析不到就保持 None）。
```

---

## 指令 5：加入简易一致性评估

```
在 decision_maker.py 中，增加一个方法 calculate_consensus(opinions: List[TraderOpinion]) -> float。

逻辑：
- 如果所有交易员方向完全一致，返回 1.0
- 如果只有两种方向且「观望」占多数，返回 0.4~0.6
- 如果做多与做空直接对立，返回 0.0~0.3
- 结合各交易员的 confidence 做加权

然后在 _synthesize 之前调用它，把结果作为参考传给决策者（或直接覆盖模型返回的 consensus_score）。
请给出清晰的实现，并添加 docstring。
```

---

## 指令 6：支持命令行选择模型与交易员

```
请增强 main.py 的命令行参数：

--model          覆盖 config 中的模型名
--traders        指定启用哪些交易员，例如 --traders institutional,senior
--demo           强制使用演示数据
--code           股票代码（已有）

同时让 config.yaml 的加载更健壮（文件不存在时给出友好提示）。
```

---

## 指令 7：编写基础测试

```
请在 multi_agent_traders/ 下创建 tests/ 目录，并编写 test_models.py：

1. 测试 TraderOpinion 和 FinalDecision 的正常创建与校验
2. 测试非法 direction 或 confidence 超出范围时会抛出 ValidationError
3. 使用 pytest
4. 不需要真实调用 LLM
```

---

## 指令 8：生成 README

```
请为 multi_agent_traders/ 生成一份清晰的 README.md，包含：

1. 项目简介与架构图（可用 mermaid 或文字）
2. 安装依赖步骤
3. 配置 API Key 的方法
4. 快速运行示例（演示数据）
5. 如何接入真实数据
6. 如何新增一个交易员角色
7. 输出结果说明
```

---

## 使用建议

- 每次只执行一条指令，检查 Cursor 的修改是否符合预期后再继续。
- 如果 Cursor 修改范围过大，可以加一句「只修改必要的文件，不要重构无关代码」。
- 提示词相关修改建议单独 commit，方便回滚与对比效果。
- 完成以上指令后，整个多智能体模块就具备了「可运行 + 可存储 + 可扩展 + 有测试」的基础生产形态。
