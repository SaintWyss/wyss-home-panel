from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
MAIN = ROOT / "firmware/src/main.cpp"
BRIDGE = ROOT / "firmware/src/adapters/bridge_client.cpp"
BRIDGE_HEADER = ROOT / "firmware/include/wyss/adapters/bridge_client.hpp"


def _function(source: str, name: str) -> str:
    match = re.search(rf"void {name}\(\) \{{(?P<body>.*?)\n\}}", source, re.DOTALL)
    assert match is not None, f"falta {name}()"
    return match.group("body")


def test_tls_waits_for_wifi_instead_of_starting_during_dhcp() -> None:
    source = MAIN.read_text(encoding="utf-8")
    assert "bridge->begin();" not in _function(source, "start_network")
    startup = _function(source, "maybe_start_bridge")
    assert "WiFi.status() != WL_CONNECTED" in startup
    assert "bridge->begin()" in startup


def test_bridge_queues_own_heap_messages_without_4k_stack_frames() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    assert source.count("xQueueCreate(6, sizeof(Message*))") == 2
    assert "new (std::nothrow) Message" in source
    assert "Message message{};" not in source
    assert source.count("delete message;") >= 2


def test_poll_before_network_start_is_safe_and_tls_has_stack_margin() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    header = BRIDGE_HEADER.read_text(encoding="utf-8")
    assert "if (inbound_ == nullptr)" in source
    runtime = _function(source, "BridgeClient::run")
    assert "WiFi.status() != WL_CONNECTED" in runtime
    assert "vTaskDelay(pdMS_TO_TICKS(250))" in runtime
    match = re.search(r"kNetworkTaskStackBytes\s*=\s*(\d+)", header)
    assert match is not None
    assert int(match.group(1)) >= 16 * 1024


def test_task_creation_failure_releases_both_queues() -> None:
    source = BRIDGE.read_text(encoding="utf-8")
    after_create = source.partition("if (xTaskCreatePinnedToCore")[2]
    failure = after_create.partition("void BridgeClient::task_entry")[0]
    assert "vQueueDelete(outbound_);" in failure
    assert "vQueueDelete(inbound_);" in failure
    assert "outbound_ = nullptr;" in failure
    assert "inbound_ = nullptr;" in failure
