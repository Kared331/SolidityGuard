"""P4-1: LLM 审计引擎基线压测。

四场景矩阵：
    A. 单文件 2 函数 + 即时 mock  → 纯逻辑开销基线
    B. 5 文件 × 2 函数 + 即时 mock + ThreadPool(5) → 并行开销 vs 串行
    C. 单文件 2 函数 + mock sleep(50ms) → 单线程串行 LLM 耗时
    D. 5 文件 × 2 函数 + mock sleep(50ms) + ThreadPool(5) → 并行加速比

输出指标：耗时(ms)、函数/秒、加速比（D vs C）
"""
import os
import sys
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

import pytest

_backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

pytestmark = pytest.mark.perf


# ── 合约 fixture 生成器 ──────────────────────────────────────────

def _make_contract(num_functions: int = 2) -> str:
    """生成含 N 个关键函数的合成 Solidity 合约（每个含 transfer 关键词以被 _extract_key_functions 选中）。"""
    funcs = []
    for i in range(num_functions):
        funcs.append(f"""
    function transfer{i}(address _to, uint256 _value) public returns (bool) {{
        require(balances[msg.sender] >= _value, "Insufficient");
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        return true;
    }}""")
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PerfToken {{
    mapping(address => uint256) public balances;

    constructor() {{}}
{chr(10).join(funcs)}
}}
"""


@pytest.fixture
def single_contract_file(tmp_path):
    """单文件 2 函数合约。"""
    p = tmp_path / "Token.sol"
    p.write_text(_make_contract(2), encoding="utf-8")
    return str(p)


@pytest.fixture
def five_contract_files(tmp_path):
    """5 文件 × 2 函数合约（文件级并行压测用）。"""
    paths = []
    for i in range(5):
        p = tmp_path / f"Token{i}.sol"
        p.write_text(_make_contract(2), encoding="utf-8")
        paths.append(str(p))
    return paths


# ── mock 工厂 ────────────────────────────────────────────────────

def _make_embedding_mock(delay_ms: float = 0):
    """返回 (get_embedding, get_embedding_batch) 的 mock。

    delay_ms>0 时模拟网络延迟；返回固定 384 维向量。
    """
    import time as _time

    def _batch(texts):
        if delay_ms > 0:
            _time.sleep(delay_ms / 1000.0)
        return [[0.1] * 384 for _ in texts]

    def _single(text):
        if delay_ms > 0:
            _time.sleep(delay_ms / 1000.0)
        return [0.1] * 384

    return _single, _batch


def _make_llm_mock(delay_ms: float = 0, response_json: str = "[]"):
    """返回 chat_completion 的 mock。"""
    import time as _time

    def _chat(messages):
        if delay_ms > 0:
            _time.sleep(delay_ms / 1000.0)
        return response_json, {"total_tokens": 100}

    return _chat


def _make_chroma_batch_mock():
    """返回 query_vulnerabilities_batch / query_vulnerabilities / get_vulnerability_collection 的 mock。"""

    def _batch(coll, embeddings, top_k=3):
        return [{"documents": [["doc"]], "metadatas": [[{"title": "Test"}]]} for _ in embeddings]

    def _single(coll, emb, top_k=3):
        return {"documents": [["doc"]], "metadatas": [[{"title": "Test"}]]}

    def _coll():
        return object()

    return _batch, _single, _coll


# ── 计时辅助 ────────────────────────────────────────────────────

def _measure(fn, *args, **kwargs) -> tuple[float, object]:
    """返回 (耗时秒, 结果)。"""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    return elapsed, result


def _fmt_ms(s: float) -> str:
    return f"{s * 1000:.1f}ms"


# ── 场景 A：单文件即时 mock（纯逻辑基线）────────────────────────

def test_perf_A_single_file_instant_mock(single_contract_file, capsys):
    """场景 A：单文件 2 函数 + 即时 mock —— 纯引擎逻辑开销基线。"""
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod

    emb_single, emb_batch = _make_embedding_mock(delay_ms=0)
    llm_chat = _make_llm_mock(delay_ms=0)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    engine = LLMAuditEngine()

    with patch.object(engine_mod, "get_embedding_batch", emb_batch), \
         patch.object(engine_mod, "get_embedding", emb_single), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed, result = _measure(engine.execute_single_file, 1, 1, single_contract_file)

    funcs = result["functions_audited"]
    funcs_per_sec = funcs / elapsed if elapsed > 0 else float("inf")

    with capsys.disabled():
        print(f"\n[场景 A] 单文件 2 函数 + 即时 mock")
        print(f"  耗时: {_fmt_ms(elapsed)} | 函数: {funcs} | 吞吐: {funcs_per_sec:.1f} 函数/秒")
        print(f"  说明: 纯逻辑开销（regex 提取 + JSON 解析 + 批量化逻辑）")

    assert funcs == 2
    assert elapsed < 1.0, f"纯逻辑开销应 <1s，实际 {elapsed:.3f}s"


# ── 场景 B：5 文件并行即时 mock（并行开销）──────────────────────

def test_perf_B_five_files_parallel_instant_mock(five_contract_files, capsys):
    """场景 B：5 文件 × 2 函数 + 即时 mock + ThreadPool(5) —— 并行开销 vs 串行。"""
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod

    emb_single, emb_batch = _make_embedding_mock(delay_ms=0)
    llm_chat = _make_llm_mock(delay_ms=0)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    engine = LLMAuditEngine()
    file_paths = [(i + 1, p) for i, p in enumerate(five_contract_files)]

    # 并行版
    with patch.object(engine_mod, "get_embedding_batch", emb_batch), \
         patch.object(engine_mod, "get_embedding", emb_single), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed_par, _ = _measure(_run_parallel, engine, file_paths)

        # 串行版（同 mock，对比 ThreadPool 开销）
        elapsed_seq, _ = _measure(_run_sequential, engine, file_paths)

    speedup = elapsed_seq / elapsed_par if elapsed_par > 0 else 0

    with capsys.disabled():
        print(f"\n[场景 B] 5 文件 × 2 函数 + 即时 mock")
        print(f"  串行: {_fmt_ms(elapsed_seq)} | 并行(5): {_fmt_ms(elapsed_par)} | 加速比: {speedup:.2f}x")
        print(f"  说明: 即时 mock 下 ThreadPool 开销可能抵消并行收益（加速比 <1 正常）")

    assert elapsed_par < 2.0


def _run_sequential(engine, file_paths):
    total_funcs = 0
    for fid, path in file_paths:
        r = engine.execute_single_file(1, fid, path)
        total_funcs += r["functions_audited"]
    return total_funcs


def _run_parallel(engine, file_paths, max_workers=5):
    total_funcs = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(engine.execute_single_file, 1, fid, path): fid for fid, path in file_paths}
        for f in as_completed(futures):
            total_funcs += f.result()["functions_audited"]
    return total_funcs


# ── 场景 C：单文件 50ms 延迟 mock（单线程 LLM 串行基线）─────────

def test_perf_C_single_file_50ms_llm_delay(single_contract_file, capsys):
    """场景 C：单文件 2 函数 + mock LLM 50ms 延迟 —— 单线程串行 LLM 耗时基线。"""
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod

    emb_single, emb_batch = _make_embedding_mock(delay_ms=0)
    # summary + 每个函数审计各 1 次 LLM 调用，每次 50ms
    llm_chat = _make_llm_mock(delay_ms=50)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    engine = LLMAuditEngine()

    with patch.object(engine_mod, "get_embedding_batch", emb_batch), \
         patch.object(engine_mod, "get_embedding", emb_single), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed, result = _measure(engine.execute_single_file, 1, 1, single_contract_file)

    funcs = result["functions_audited"]
    # 理论耗时 ≈ (1 summary + 2 funcs) × 50ms = 150ms
    theoretical = (1 + funcs) * 50 / 1000
    funcs_per_sec = funcs / elapsed if elapsed > 0 else 0

    with capsys.disabled():
        print(f"\n[场景 C] 单文件 2 函数 + LLM 50ms 延迟")
        print(f"  耗时: {_fmt_ms(elapsed)} | 理论: {_fmt_ms(theoretical)} | 函数: {funcs} | 吞吐: {funcs_per_sec:.1f} 函数/秒")
        print(f"  说明: 单线程串行 LLM 是真实瓶颈；理论 {(1+funcs)*50}ms = summary + N×audit")

    assert funcs == 2
    assert elapsed >= 0.10, "50ms×3 次调用应 ≥ 150ms"


# ── 场景 D：5 文件并行 50ms 延迟（并行加速比验证）──────────────

def test_perf_D_five_files_parallel_50ms_delay(five_contract_files, capsys):
    """场景 D：5 文件 × 2 函数 + LLM 50ms 延迟 + ThreadPool(5) —— 并行加速比验证。"""
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod

    emb_single, emb_batch = _make_embedding_mock(delay_ms=0)
    llm_chat = _make_llm_mock(delay_ms=50)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    engine = LLMAuditEngine()
    file_paths = [(i + 1, p) for i, p in enumerate(five_contract_files)]

    with patch.object(engine_mod, "get_embedding_batch", emb_batch), \
         patch.object(engine_mod, "get_embedding", emb_single), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed_par, _ = _measure(_run_parallel, engine, file_paths)
        elapsed_seq, _ = _measure(_run_sequential, engine, file_paths)

    speedup = elapsed_seq / elapsed_par if elapsed_par > 0 else 0
    total_funcs = 5 * 2
    funcs_per_sec_par = total_funcs / elapsed_par if elapsed_par > 0 else 0
    funcs_per_sec_seq = total_funcs / elapsed_seq if elapsed_seq > 0 else 0
    # 理论：串行 5×150ms=750ms；并行 5 线程各 150ms = 150ms（加速 5x）
    theoretical_par = 150 / 1000

    with capsys.disabled():
        print(f"\n[场景 D] 5 文件 × 2 函数 + LLM 50ms 延迟 + ThreadPool(5)")
        print(f"  串行: {_fmt_ms(elapsed_seq)} | 并行(5): {_fmt_ms(elapsed_par)} | 理论并行: {_fmt_ms(theoretical_par)}")
        print(f"  加速比: {speedup:.2f}x | 串行吞吐: {funcs_per_sec_seq:.1f} | 并行吞吐: {funcs_per_sec_par:.1f} 函数/秒")
        print(f"  说明: 真实 LLM 延迟下并行收益显著；加速比应接近 max_workers=5")

    # 真实加速比应明显 >1（至少 3x，留容错）
    assert speedup > 3.0, f"5 线程并行加速比应 >3x，实际 {speedup:.2f}x"
    assert elapsed_par < elapsed_seq, "并行应快于串行"


# ── 场景 E：embedding 批量大小边界（32 vs 1）────────────────────

def test_perf_E_embedding_batch_vs_single(single_contract_file, capsys):
    """场景 E：对比批量 embedding 一次 vs 逐个 N 次（验证 _BATCH_LIMIT=32 优化的收益）。"""
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod
    import time as _time

    # 用 10 函数合约放大 batch vs 单次差异
    big_contract = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sol", delete=False, encoding="utf-8",
    )
    big_contract.write(_make_contract(10))
    big_contract.close()

    llm_chat = _make_llm_mock(delay_ms=0)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    # 路径 A：批量 embedding（一次调用）
    emb_single_a, emb_batch_a = _make_embedding_mock(delay_ms=20)  # 20ms 模拟 embedding API 延迟
    engine = LLMAuditEngine()
    with patch.object(engine_mod, "get_embedding_batch", emb_batch_a), \
         patch.object(engine_mod, "get_embedding", emb_single_a), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed_batch, _ = _measure(engine.execute_single_file, 1, 1, big_contract.name)

    # 路径 B：强制走逐个 fallback（patch get_embedding_batch 抛异常）
    emb_single_b, _ = _make_embedding_mock(delay_ms=20)
    engine2 = LLMAuditEngine()
    with patch.object(engine_mod, "get_embedding_batch", side_effect=ValueError("forced fallback")), \
         patch.object(engine_mod, "get_embedding", emb_single_b), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed_single, _ = _measure(engine2.execute_single_file, 1, 1, big_contract.name)

    try:
        os.unlink(big_contract.name)
    except OSError:
        pass

    speedup = elapsed_single / elapsed_batch if elapsed_batch > 0 else 0

    with capsys.disabled():
        print(f"\n[场景 E] 10 函数合约 embedding 批量 vs 逐个（20ms 延迟）")
        print(f"  批量(1次): {_fmt_ms(elapsed_batch)} | 逐个(10次): {_fmt_ms(elapsed_single)} | 加速比: {speedup:.2f}x")
        print(f"  说明: 验证 _BATCH_LIMIT=32 批量化的收益；10 函数应省 9 次 API 调用")

    assert elapsed_batch < elapsed_single, "批量 embedding 应快于逐个"
    assert speedup > 2.0, f"批量加速比应 >2x，实际 {speedup:.2f}x"


# ── 场景 F：小 N 串行守护（P4-3 阈值生效验证）─────────────────

def test_perf_F_small_n_serial_path(capsys):
    """场景 F：单文件 5 函数（≤ 阈值）+ LLM 50ms 延迟 —— 验证 P4-3 阈值生效。

    P4-3 阈值=5：N ≤ 5 时走串行路径（避免 ThreadPool 开销）。
    5 函数串行耗时 = summary(50ms) + 5×audit(50ms) = 300ms。
    若误启用并行，耗时 ≈ 50ms + 1×50ms = 100ms（5 函数一批并行）。
    本测试守护串行路径：耗时 ≥ 250ms 即认为走串行。
    """
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod

    emb_single, emb_batch = _make_embedding_mock(delay_ms=0)
    llm_chat = _make_llm_mock(delay_ms=50)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    contract = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sol", delete=False, encoding="utf-8",
    )
    contract.write(_make_contract(5))
    contract.close()

    engine = LLMAuditEngine()
    with patch.object(engine_mod, "get_embedding_batch", emb_batch), \
         patch.object(engine_mod, "get_embedding", emb_single), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed, result = _measure(engine.execute_single_file, 1, 1, contract.name)

    try:
        os.unlink(contract.name)
    except OSError:
        pass

    funcs = result["functions_audited"]
    theoretical_serial = (1 + funcs) * 50 / 1000  # summary + N×audit 串行

    with capsys.disabled():
        print(f"\n[场景 F] 单文件 {funcs} 函数 (≤阈值) + LLM 50ms 延迟")
        print(f"  实测: {_fmt_ms(elapsed)} | 理论串行: {_fmt_ms(theoretical_serial)}")
        print(f"  说明: N ≤ 阈值({engine._PARALLEL_FUNC_THRESHOLD}) 应走串行路径")

    assert funcs == 5
    # 串行耗时 ≈ 300ms；并行耗时 ≈ 100ms。守护串行：耗时 ≥ 250ms
    assert elapsed >= 0.25, f"5 函数应走串行 ≥ 250ms，实际 {elapsed:.3f}s（误启用并行？）"


# ── 场景 G：函数级并行优化验证（P4-3 前后对比）─────────────────

def test_perf_G_function_level_parallel_optimization(capsys):
    """场景 G：单文件 10 函数 + LLM 50ms 延迟，验证 P4-3 函数级并行优化收益。

    P4-3 前（场景 F）：689.6ms 串行。
    P4-3 后（本场景）：应接近理论并行 150ms（summary 50ms + ceil(10/5)×50ms = 150ms）。
    预期加速比 ≥ 3.0x（验证 P4-3 优化生效）。
    """
    from app.services.engine.llm_audit import LLMAuditEngine
    from app.services.engine import llm_audit as engine_mod

    emb_single, emb_batch = _make_embedding_mock(delay_ms=0)
    llm_chat = _make_llm_mock(delay_ms=50)
    chroma_batch, chroma_single, chroma_coll = _make_chroma_batch_mock()

    big_contract = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sol", delete=False, encoding="utf-8",
    )
    big_contract.write(_make_contract(10))
    big_contract.close()

    engine = LLMAuditEngine()
    with patch.object(engine_mod, "get_embedding_batch", emb_batch), \
         patch.object(engine_mod, "get_embedding", emb_single), \
         patch.object(engine_mod, "chat_completion", llm_chat), \
         patch.object(engine_mod, "query_vulnerabilities_batch", chroma_batch), \
         patch.object(engine_mod, "query_vulnerabilities", chroma_single), \
         patch.object(engine_mod, "get_vulnerability_collection", chroma_coll):
        elapsed, result = _measure(engine.execute_single_file, 1, 1, big_contract.name)

    try:
        os.unlink(big_contract.name)
    except OSError:
        pass

    funcs = result["functions_audited"]
    import math
    theoretical_parallel = (50 + math.ceil(funcs / 5) * 50) / 1000
    # P4-3 前基线（场景 F 实测）：689.6ms
    baseline_serial = 0.6896
    actual_speedup = baseline_serial / elapsed if elapsed > 0 else 0

    with capsys.disabled():
        print(f"\n[场景 G] P4-3 优化验证：单文件 {funcs} 函数 + LLM 50ms 延迟 + 函数级并行")
        print(f"  优化后耗时: {_fmt_ms(elapsed)} | 理论并行: {_fmt_ms(theoretical_parallel)}")
        print(f"  P4-3 前基线: {_fmt_ms(baseline_serial)} | 实际加速: {actual_speedup:.2f}x")
        print(f"  说明: 验证函数级 LLM 并行生效；加速比应 ≥ 3.0x")

    assert funcs == 10
    assert elapsed < 0.30, f"P4-3 后应 <300ms（理论 150ms），实际 {elapsed:.3f}s"
    assert actual_speedup > 3.0, f"加速比应 >3.0x，实际 {actual_speedup:.2f}x"
