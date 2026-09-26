# AI Quant 2026 — 课程现代化重构包

本目录包含从 2025 年 1 月「AI量化入门」课程中提取并升级的核心组件。

## 目录结构

```
ai_quant_2026/
├── multi_agent_traders/          # 多智能体交易员系统（完整可运行）
│   ├── agents/                   # 各交易员实现
│   ├── prompts/                  # 角色提示词（独立可热更新）
│   ├── models.py                 # Pydantic 数据模型
│   ├── decision_maker.py         # 决策者
│   ├── data_provider.py          # 数据与指标
│   ├── config.yaml               # 配置
│   ├── main.py                   # 入口
│   └── requirements.txt
├── livermore_analyzer/           # 利弗莫尔分析独立模块
│   ├── livermore.py
│   └── __init__.py
└── docs/
    ├── 核心知识点详解.md          # 10 大核心知识点详细文档
    └── Cursor重構指令清單_多智能體模組.md
```

## 快速开始：多智能体系统

```bash
cd multi_agent_traders
pip install -r requirements.txt

# 编辑 config.yaml，填入你的 API Key
# 然后运行（默认使用演示数据）
python main.py --code 600588
```

## 快速开始：利弗莫尔分析

```python
from openai import OpenAI
from livermore_analyzer import LivermoreAnalyzer

client = OpenAI(base_url="https://api.deepseek.com/v1", api_key="sk-xxx")
analyzer = LivermoreAnalyzer(client)

result = analyzer.analyze(
    stock_code="600588",
    close=32.56,
    ma5=31.80,
    ma20=29.40,
    rsi=62.5,
    volume_ratio=1.45,
)
print(result.model_dump_json(indent=2))
```

## 设计原则

1. **结构化输出**：全部使用 Pydantic + JSON mode
2. **提示词与代码分离**：方便迭代与 A/B 测试
3. **可替换数据源**：演示数据与真实数据解耦
4. **并行多智能体**：ThreadPoolExecutor 提高效率
5. **失败降级**：单个交易员失败不影响整体流程

## 后续扩展建议

见 `docs/Cursor重構指令清單_多智能體模組.md`
