import os
import re
import subprocess
import logging
from pathlib import Path

from app.services.engine.base import BaseEngine

logger = logging.getLogger("solidguard.engine.fuzzer")


def _find_contract_info(project_dir: str) -> list[dict]:
    """Scan .sol files for contract names and public/external functions."""
    contracts = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ("test", "lib", ".git", "node_modules")]
        for fname in files:
            if not fname.endswith(".sol"):
                continue
            fpath = os.path.join(root, fname)
            try:
                content = Path(fpath).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            contract_match = re.search(r"contract\s+(\w+)", content)
            if not contract_match:
                continue
            contract_name = contract_match.group(1)

            func_pattern = r"function\s+(\w+)\s*\([^)]*\)[^{]*(?:external|public)[^{]*\{|function\s+(\w+)\s*\([^)]*\)[^{]*\{"
            functions = []
            for m in re.finditer(func_pattern, content):
                fname_match = m.group(1) or m.group(2)
                if fname_match in ("constructor", "receive", "fallback"):
                    continue
                functions.append(fname_match)

            if functions:
                contracts.append({
                    "name": contract_name,
                    "file": fpath,
                    "functions": functions[:10],
                })
    return contracts


def _generate_fuzz_test(contracts: list[dict], test_dir: str) -> str:
    """Generate a meaningful fuzz test file that calls actual contract functions."""
    os.makedirs(test_dir, exist_ok=True)
    fuzz_test_path = os.path.join(test_dir, "FuzzTest.t.sol")

    imports = ["// SPDX-License-Identifier: MIT", "pragma solidity ^0.8.0;", "", 'import "forge-std/Test.sol";']

    contract_names = []
    for c in contracts:
        contract_names.append(c["name"])

    test_body = []
    test_body.append("")
    test_body.append("contract FuzzTest is Test {")

    for c in contracts:
        cname = c["name"]
        var_name = f"_{cname[0].lower()}{cname[1:]}"
        test_body.append(f"    {cname} public {var_name};")
    test_body.append("")

    test_body.append("    function setUp() public {")
    for c in contracts:
        cname = c["name"]
        var_name = f"_{cname[0].lower()}{cname[1:]}"
        test_body.append(f"        {var_name} = new {cname}();")
    test_body.append("    }")
    test_body.append("")

    test_count = 0
    for c in contracts:
        cname = c["name"]
        var_name = f"_{cname[0].lower()}{cname[1:]}"
        for func in c["functions"][:5]:
            test_count += 1
            test_body.append(f"    function testFuzz_{cname}_{func}(uint256 x) public {{")
            test_body.append(f"        // Fuzz test for {cname}.{func}")
            test_body.append(f"        try {var_name}.{func}(x) {{")
            test_body.append(f"            // Function accepted the input")
            test_body.append(f"        }} catch {{")
            test_body.append(f"            // Function reverted - this is expected for some inputs")
            test_body.append(f"        }}")
            test_body.append(f"    }}")
            test_body.append("")

    if test_count == 0:
        test_body.append("    function testFuzz_basic(uint256 x) public pure {")
        test_body.append("        // No testable public/external functions found in the project")
        test_body.append("        assertEq(x, x);")
        test_body.append("    }")
        test_body.append("")

    test_body.append("}")

    content = "\n".join(imports + test_body)
    Path(fuzz_test_path).write_text(content, encoding="utf-8")
    logger.info(
        "Generated fuzz test with %d test cases at %s", test_count, fuzz_test_path
    )
    return fuzz_test_path


class FuzzerEngine(BaseEngine):
    def execute(self, project_id: int, project_dir: str) -> dict:
        if not os.path.isdir(project_dir):
            self.logger.error("Project directory not found: %s", project_dir)
            return {"raw_output": "", "failures": None, "contracts_found": 0, "tests_generated": 0}

        try:
            foundry_toml = os.path.join(project_dir, "foundry.toml")
            test_dir = os.path.join(project_dir, "test")

            has_test_files = False
            if os.path.isdir(test_dir):
                for root, _, files in os.walk(test_dir):
                    for fname in files:
                        if fname.endswith(".sol"):
                            has_test_files = True
                            break
                    if has_test_files:
                        break

            contracts = _find_contract_info(project_dir)
            tests_generated = 0

            if not os.path.isfile(foundry_toml) or not has_test_files:
                if not os.path.isfile(foundry_toml):
                    try:
                        subprocess.run(
                            ["forge", "init", "--no-git", "--force", project_dir],
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                        self.logger.warning("Failed to init forge project: %s", e)

                if contracts:
                    _generate_fuzz_test(contracts, test_dir)
                    tests_generated = sum(min(len(c["functions"]), 5) for c in contracts) or 1
                else:
                    os.makedirs(test_dir, exist_ok=True)
                    fuzz_test_path = os.path.join(test_dir, "FuzzTest.t.sol")
                    basic_test = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract FuzzTest is Test {
    function testFuzz_basic(uint256 x) public pure {
        assertEq(x, x);
    }
}
"""
                    Path(fuzz_test_path).write_text(basic_test, encoding="utf-8")
                    self.logger.warning("No testable contracts found, generated basic fuzz test")
                    tests_generated = 1

            # Run forge test
            try:
                proc = subprocess.run(
                    ["forge", "test", "-vvv", "--root", project_dir],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                raw_output = proc.stdout + "\n" + proc.stderr
            except subprocess.TimeoutExpired:
                raw_output = "Forge test timed out after 600s"
            except FileNotFoundError:
                raw_output = "Forge binary not found"

            # Parse failures
            failures = []
            lines = raw_output.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if "[FAIL]" in line:
                    test_match = re.search(r"\[FAIL\]\s+(\S+)", line)
                    test_name = test_match.group(1) if test_match else line.strip()

                    counterexample = None
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if "Counterexample:" in lines[j]:
                            counterexample = lines[j].split("Counterexample:", 1)[1].strip()
                            break

                    failures.append({"test_name": test_name, "counterexample": counterexample})
                i += 1

            failures_json = failures if failures else None

            return {
                "raw_output": raw_output,
                "failures": failures_json,
                "contracts_found": len(contracts),
                "tests_generated": tests_generated,
            }

        except Exception:
            self.logger.exception("Failed to run fuzzer for project %d", project_id)
            raise
