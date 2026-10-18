"""6A 回归：故障注入下账本必须标记，且单元不丢失。

实验本体在 `docs/evidence/run_6a.py`（100×4 次注入）；这里跑一个小规模版本，
防止后续改动把"故障可见"或"单元守恒"弄坏。
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs" / "evidence" / "run_6a.py"


def _load_experiment():
    spec = importlib.util.spec_from_file_location("run_6a", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def experiment():
    return _load_experiment()


@pytest.fixture(scope="module")
def pool(experiment):
    return experiment.contract_pool()


@pytest.mark.parametrize("fault", ["budget", "rag_failure", "llm_error", "parse_error"])
def test_each_fault_is_marked(experiment, pool, fault):
    for seed in range(3):
        paths = [pool[seed % len(pool)]]
        facts = experiment.run_once(paths, fault, seed=seed)
        assert experiment.marked(facts), facts


def test_ledger_units_equal_extraction(experiment, pool):
    experiment.install_stubs()
    for i, path in enumerate(pool[:3]):
        text = path.read_text(encoding="utf-8", errors="ignore")
        expected = len(experiment.extract_functions(text))
        result = experiment.mod.LLMAuditEngine().execute_single_file(1, i, str(path))
        coverage = experiment.build_coverage([result], files_total=1)

        assert coverage["functions_extracted"] == expected
        assert coverage["functions_extracted"] == (
            coverage["functions_audited"]
            + coverage["functions_skipped"]
            + coverage["functions_failed"]
            + coverage["functions_filtered"]
        )
