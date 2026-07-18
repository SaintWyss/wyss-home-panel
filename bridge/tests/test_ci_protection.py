from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
CHECKER = ROOT / "tools" / "check_ci_protection.py"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CONTRACT = ROOT / ".github" / "required-checks.json"
COMMIT = "a" * 40


def _run(*args: str, payload: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Python interpreter and checker
        [sys.executable, str(CHECKER), *args],
        cwd=ROOT,
        input=json.dumps(payload) if payload is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )


def _mutated(tmp_path: Path, old: str, new: str) -> Path:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert old in source
    target = tmp_path / "ci.yml"
    target.write_text(source.replace(old, new, 1), encoding="utf-8")
    return target


def _check_runs() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return {
        "total_count": 5,
        "check_runs": [
            {
                "name": item["name"],
                "head_sha": COMMIT,
                "status": "completed",
                "conclusion": "success",
            }
            for item in contract["checks"]
        ],
    }


def _remote() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": [item["name"] for item in contract["checks"]],
        },
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "required_approving_review_count": 1,
        },
        "required_conversation_resolution": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }


def test_local_contract_passes() -> None:
    result = _run("--local")
    assert result.returncode == 0, result.stderr
    assert set(json.loads(result.stdout)["jobs"]) == {
        "domain",
        "bridge",
        "firmware",
        "secrets",
        "docs",
    }


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("  docs:\n", "  docs_removed:\n"),
        (
            "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
            "actions/checkout@v4",
        ),
        (
            "gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7",
            "gitleaks/gitleaks-action@" + "b" * 40,
        ),
        (
            "python tools/check_docs.py --format json",
            "python -c 'print(\"docs skipped\")'",
        ),
    ],
)
def test_local_contract_rejects_unsafe_mutations(tmp_path: Path, old: str, new: str) -> None:
    workflow = _mutated(tmp_path, old, new)
    assert _run("--local", "--workflow", str(workflow)).returncode == 1


def test_check_runs_require_five_successes_on_exact_sha() -> None:
    payload = _check_runs()
    result = _run("--check-runs-json", "-", "--tested-commit", COMMIT, payload=payload)
    assert result.returncode == 0, result.stderr


def test_check_runs_accept_completed_push_and_pr_reexecutions() -> None:
    payload = _check_runs()
    payload["check_runs"] += [dict(item) for item in payload["check_runs"]]
    payload["total_count"] = 10

    result = _run("--check-runs-json", "-", "--tested-commit", COMMIT, payload=payload)

    assert result.returncode == 0, result.stderr
    assert set(json.loads(result.stdout)["occurrences"].values()) == {2}


@pytest.mark.parametrize("state", ["in_progress", "failure", "unexpected"])
def test_check_runs_reject_unsafe_duplicate_execution(state: str) -> None:
    payload = _check_runs()
    duplicate = dict(payload["check_runs"][0])
    if state == "in_progress":
        duplicate.update(status="in_progress", conclusion=None)
    elif state == "failure":
        duplicate["conclusion"] = "failure"
    else:
        duplicate["name"] = "untrusted-check"
    payload["check_runs"].append(duplicate)

    result = _run("--check-runs-json", "-", "--tested-commit", COMMIT, payload=payload)

    assert result.returncode == 1


@pytest.mark.parametrize("mutation", ["missing", "sha", "conclusion"])
def test_check_runs_reject_incomplete_or_untrusted_results(mutation: str) -> None:
    payload = _check_runs()
    if mutation == "missing":
        payload["check_runs"].pop()
    elif mutation == "sha":
        payload["check_runs"][0]["head_sha"] = "b" * 40
    else:
        payload["check_runs"][0]["conclusion"] = "failure"
    result = _run("--check-runs-json", "-", "--tested-commit", COMMIT, payload=payload)
    assert result.returncode == 1


def test_remote_protection_requires_all_controls() -> None:
    result = _run("--remote-json", "-", payload=_remote())
    assert result.returncode == 0, result.stderr


def test_remote_protection_rejects_force_pushes() -> None:
    payload = _remote()
    payload["allow_force_pushes"]["enabled"] = True
    assert _run("--remote-json", "-", payload=payload).returncode == 1
