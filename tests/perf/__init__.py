"""性能压测套件（P4）。

运行方式：
    pytest -m perf                          # 全部 perf 测试
    pytest tests/perf/test_engine_perf.py   # 单文件

设计目标：
    1. 隔离 LLM/embedding 网络延迟，测纯引擎逻辑开销
    2. 验证文件级并行的实际加速比
    3. 量化 mock 延迟下的吞吐瓶颈，识别优化方向
"""
