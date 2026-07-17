from __future__ import annotations

import ast
from pathlib import Path

from wyss_panel_bridge import ports_v2

ROOT = Path(__file__).parents[2]


def test_all_v2_capabilities_have_small_ports() -> None:
    expected = {
        "HomePort",
        "LightPort",
        "ProjectionPort",
        "ClientEventPort",
        "MediaPort",
        "WeatherPort",
        "CalendarPort",
        "ReminderPort",
        "TimerPort",
        "NotificationPort",
        "SpeechPort",
        "CameraPort",
    }
    assert expected <= set(vars(ports_v2))
    source = (ROOT / "bridge/src/wyss_panel_bridge/ports_v2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    methods = {
        node.name: len(
            [
                child
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        )
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name in expected
    }
    assert set(methods) == expected
    assert all(1 <= count <= 3 for count in methods.values())


def test_v1_runtime_does_not_import_v2_contracts() -> None:
    runtime = [
        ROOT / "bridge/src/wyss_panel_bridge/api.py",
        ROOT / "bridge/src/wyss_panel_bridge/application/session_service.py",
    ]
    for path in runtime:
        source = path.read_text(encoding="utf-8")
        assert "protocol_v2" not in source
        assert "ports_v2" not in source
