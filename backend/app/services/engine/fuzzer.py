"""Foundry fuzzing: generate only tests that can fail.

The previous implementation generated `try target.f(x) {} catch {}` with a
single `assertEq(x, x)` — a test that cannot fail, and which did not even
compile (missing import, constructor args, parameter types). See
docs/evidence/fuzz-baseline.md.

This version:
  * copies the project to a temp workspace (never mutates the upload dir),
  * imports the contract and passes real constructor arguments,
  * emits ONE invariant test per contract and only when the invariant is
    derivable from the source: ERC-20 style conservation
    (`totalSupply` + balance getter + `transfer(address,uint256)` + a
    single-uint payout function),
  * reports `skipped_reason` when nothing can be derived instead of
    generating a tautology,
  * caps raw output at 64 KB and records `status` in the output header.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.services.engine.base import BaseEngine
from app.services.engine.solidity_units import extract_functions, mask_source

logger = logging.getLogger("solidguard.engine.fuzzer")

MAX_RAW_OUTPUT = 64 * 1024
FORGE_TIMEOUT = 600

_UINT_RE = re.compile(r"^u?int\d*$")
_BYTES_RE = re.compile(r"^bytes\d+$")
_SUPPORTED_SCALARS = {"address", "bool"}


@dataclass
class Param:
    solidity_type: str
    fuzz_type: str | None  # None -> unsupported, function skipped

    @property
    def cast(self) -> str:
        if self.solidity_type == "address":
            return "address(uint160({}))"
        if self.solidity_type in ("bool", "string", "bytes"):
            return "{}"
        if self.solidity_type.startswith("bytes") and self.solidity_type != "bytes":
            return f"{self.solidity_type}({{}})"
        return f"{self.solidity_type}({{}})"


@dataclass
class FnInfo:
    name: str
    params: list[Param]
    view: bool


@dataclass
class ContractInfo:
    name: str
    rel_import: str | None
    source_path: str = ""
    constructor_params: list[Param] = field(default_factory=list)
    functions: list[FnInfo] = field(default_factory=list)


def _split_params(raw: str) -> list[str]:
    parts, depth, current = [], 0, []
    for ch in raw:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if "".join(current).strip():
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _normalize_param(raw: str) -> Param:
    tokens = [t for t in raw.replace("\n", " ").split() if t not in ("memory", "calldata", "storage")]
    if not tokens:
        return Param("unsupported", None)
    sol_type = tokens[0]
    if sol_type == "address" and len(tokens) > 1 and tokens[1] == "payable":
        sol_type = "address"
    if sol_type == "uint":
        sol_type = "uint256"
    if sol_type == "int":
        sol_type = "int256"

    if sol_type in _SUPPORTED_SCALARS:
        return Param(sol_type, "bool" if sol_type == "bool" else "uint256")
    if _UINT_RE.match(sol_type):
        return Param(sol_type, "uint256")
    if _BYTES_RE.match(sol_type):
        return Param(sol_type, "bytes32")
    return Param(sol_type, None)  # string/bytes/array/struct/contract type


def _signature_params(masked: str, name: str) -> list[Param]:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(([^)]*)\)", masked, re.DOTALL)
    if not match:
        return []
    return [_normalize_param(p) for p in _split_params(match.group(1))]


def _constructor_params(masked: str) -> list[Param]:
    match = re.search(r"\bconstructor\s*\(([^)]*)\)", masked, re.DOTALL)
    if not match:
        return []
    return [_normalize_param(p) for p in _split_params(match.group(1))]


def _signature_tail(masked: str, name: str) -> str:
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\([^)]*\)([^{{;]*)\{{", masked, re.DOTALL)
    return match.group(1) if match else ""


def _visibility_ok(masked: str, name: str) -> bool:
    tail = _signature_tail(masked, name)
    return ("public" in tail or "external" in tail) and "internal" not in tail and "private" not in tail


def _parse_contracts(project_dir: str) -> list[ContractInfo]:
    contracts: list[ContractInfo] = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ("test", "lib", ".git", "node_modules", "out", "cache")]
        for fname in sorted(files):
            if not fname.endswith(".sol"):
                continue
            path = os.path.join(root, fname)
            try:
                content = Path(path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            masked = mask_source(content)
            concrete = re.search(r"\bcontract\s+(\w+)", masked)
            if not concrete:
                continue
            # Skip `abstract contract` and pure interface files.
            if re.search(r"\babstract\s+contract\s+" + re.escape(concrete.group(1)) + r"\b", masked):
                continue

            name = concrete.group(1)
            ctor = _constructor_params(masked)
            functions = []
            for unit in extract_functions(content):
                if unit.kind != "function" or not _visibility_ok(masked, unit.name):
                    continue
                functions.append(
                    FnInfo(
                        name=unit.name,
                        params=_signature_params(masked, unit.name),
                        view=bool(re.search(r"\b(view|pure)\b", _signature_tail(masked, unit.name))),
                    )
                )
            if not functions:
                continue
            rel = os.path.relpath(path, os.path.join(project_dir, "test")).replace(os.sep, "/")
            contracts.append(
                ContractInfo(
                    name=name,
                    rel_import=rel,
                    source_path=path,
                    constructor_params=ctor,
                    functions=functions,
                )
            )
    return contracts


def _balance_getter(contract: ContractInfo) -> str | None:
    names = {f.name for f in contract.functions}
    if "balanceOf" in names:
        return "balanceOf"
    return None


def _conservation_test(contract: ContractInfo, content: str) -> str | None:
    """ERC-20 conservation: sum(balances) == totalSupply after a payout."""
    getter = _balance_getter(contract)
    if getter is None:
        if not re.search(r"mapping\s*\([^)]*\)\s*public\s+balances\b", content):
            return None
        getter = "balances"

    names = {f.name: f for f in contract.functions}
    transfer = names.get("transfer")
    if transfer is None or len(transfer.params) != 2 or transfer.view:
        return None
    if transfer.params[1].solidity_type not in ("uint256", "uint"):
        return None

    payouts = [
        f
        for f in contract.functions
        if len(f.params) == 1 and f.params[0].solidity_type.startswith("uint") and not f.view
    ]
    if not payouts:
        return None
    payout = payouts[0]

    return f"""    function testFuzz_{contract.name}_Conservation_{payout.name}(uint256 seed0, uint256 seed1) public {{
        vm.deal(address(target), 1 ether);
        address actor = address(uint160(seed0 | 0x1000));
        uint256 supply = target.totalSupply();
        uint256 amount = bound(seed1, 0, supply);
        try target.transfer(actor, amount) {{}} catch {{}}
        uint256 held = target.{getter}(actor);
        vm.prank(actor);
        try target.{payout.name}(held) {{}} catch {{}}
        assertEq(target.{getter}(actor) + target.{getter}(address(this)), supply);
    }}
"""


def _ctor_value(param: Param) -> str | None:
    """A non-degenerate placeholder so invariants are not tested on an empty contract."""
    if param.solidity_type == "address":
        return "address(0x1)"
    if param.solidity_type == "bool":
        return "false"
    if _UINT_RE.match(param.solidity_type):
        # 1 keeps narrow types (uint8/uint16) valid at compile time.
        return "1"
    if _BYTES_RE.match(param.solidity_type):
        return "0"
    if param.solidity_type == "string":
        return '""'
    if param.solidity_type == "bytes":
        return 'hex""'
    return None


def _generate_tests(contracts: list[tuple[ContractInfo, str]], test_dir: str) -> tuple[str | None, int, str]:
    os.makedirs(test_dir, exist_ok=True)
    path = os.path.join(test_dir, "SolidGuardFuzz.t.sol")

    imports = ["// SPDX-License-Identifier: MIT", "pragma solidity ^0.8.0;", "", 'import "forge-std/Test.sol";']
    bodies: list[str] = []
    tests = 0

    for contract, content in contracts:
        if not contract.rel_import:
            continue
        imports.append(f'import "{contract.rel_import}";')

        ctor_values = [_ctor_value(p) for p in contract.constructor_params]
        if any(v is None for v in ctor_values):
            continue  # unsupported constructor params: cannot deploy
        ctor_args = ", ".join(p.cast.format(v) for p, v in zip(contract.constructor_params, ctor_values, strict=True))

        test = _conservation_test(contract, content)
        if test is None:
            continue
        tests += 1
        bodies.append(
            f"""
contract Fuzz_{contract.name} is Test {{
    {contract.name} internal target;

    function setUp() public {{
        target = new {contract.name}({ctor_args});
    }}

{test}}}
"""
        )

    if tests == 0:
        return None, 0, "no_invariant_derivable"

    header = "\n".join(imports) + "\n"
    Path(path).write_text(header + "\n".join(bodies), encoding="utf-8")
    return path, tests, "ok"


def _run_forge(root: str) -> tuple[str, str]:
    # forge resolves cache/out against the process cwd even with --root set;
    # pin them inside the workspace so the app directory stays clean.
    env = {
        **os.environ,
        "FOUNDRY_CACHE_PATH": os.path.join(root, "cache"),
        "FOUNDRY_OUT": os.path.join(root, "out"),
    }
    try:
        proc = subprocess.run(
            ["forge", "test", "-vvv", "--root", root, "--match-path", "test/SolidGuardFuzz.t.sol"],
            capture_output=True,
            text=True,
            timeout=FORGE_TIMEOUT,
            env=env,
            cwd=root,
        )
    except subprocess.TimeoutExpired:
        return f"Forge test timed out after {FORGE_TIMEOUT}s", "timeout"
    except FileNotFoundError:
        return "forge binary not found", "forge_missing"

    output = (proc.stdout + "\n" + proc.stderr)[:MAX_RAW_OUTPUT]
    if "[FAIL" in output:
        return output, "ok"
    if "Compiler run failed" in output or "Error (" in output:
        return output, "compile_error"
    return output, "ok"


def _parse_failures(output: str) -> list[dict]:
    """Forge prints a failing test twice (suite summary + Failing tests block)."""
    failures: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for line in output.splitlines():
        if "[FAIL" not in line or "testFuzz_" not in line:
            continue
        name_match = re.search(r"(testFuzz_\w+)\s*\(", line)
        if not name_match:
            continue
        test_name = name_match.group(1)
        ce_match = re.search(r"counterexample:\s*([^\]]+)", line)
        counterexample = ce_match.group(1).strip()[:500] if ce_match else None
        key = (test_name, counterexample or "")
        if key in seen:
            continue
        seen.add(key)

        # testFuzz_<Contract>_Conservation_<payout>
        parts = test_name.split("_")
        contract = parts[1] if len(parts) > 1 else ""
        function = parts[3] if len(parts) > 3 else ""
        failures.append(
            {
                "test_name": test_name,
                "counterexample": counterexample,
                "contract": contract,
                "function": function,
                "risk_type": "supply_conservation",
            }
        )
    return failures


class FuzzerEngine(BaseEngine):
    def _workspace(self, project_dir: str) -> str:
        tmp = tempfile.mkdtemp(prefix="sg-fuzz-")
        shutil.copytree(
            project_dir,
            tmp,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "out", "cache", "node_modules"),
        )
        return tmp

    def execute(self, project_id: int, project_dir: str) -> dict:
        if not os.path.isdir(project_dir):
            self.logger.error("Project directory not found: %s", project_dir)
            return {
                "raw_output": "",
                "failures": None,
                "contracts_found": 0,
                "tests_generated": 0,
                "status": "missing_dir",
            }

        workspace = self._workspace(project_dir)
        try:
            if not os.path.isfile(os.path.join(workspace, "foundry.toml")):
                try:
                    subprocess.run(
                        ["forge", "init", "--no-git", "--force", workspace],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        cwd=workspace,
                    )
                except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                    self.logger.warning("forge init failed: %s", exc)

            parsed = []
            for contract in _parse_contracts(workspace):
                source = Path(contract.source_path).read_text(encoding="utf-8", errors="ignore")
                parsed.append((contract, source))

            tests_path, tests_generated, reason = _generate_tests(parsed, os.path.join(workspace, "test"))

            if tests_generated == 0:
                return {
                    "raw_output": f"[fuzz-status] status={reason} contracts={len(parsed)}",
                    "failures": None,
                    "contracts_found": len(parsed),
                    "tests_generated": 0,
                    "status": reason,
                }

            output, status = _run_forge(workspace)
            failures = _parse_failures(output) if status == "ok" else []
            output = f"[fuzz-status] status={status} tests={tests_generated} file={tests_path}\n" + output

            return {
                "raw_output": output,
                "failures": failures or None,
                "contracts_found": len(parsed),
                "tests_generated": tests_generated,
                "status": status,
            }
        except Exception:
            self.logger.exception("Failed to run fuzzer for project %d", project_id)
            raise
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
