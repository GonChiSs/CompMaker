from __future__ import annotations

import json
import os
import requests
import sys
import time
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from logic import meta_build_fetcher
from logic.genetic_build_optimizer import OptimizationTarget
from logic.lol_knowledge_base import KnowledgeBase
from logic.meta_build_fetcher import _build_champion_slug
from logic.meta_build_fetcher import _extract_meta_from_qdata
from logic.meta_build_fetcher import infer_target_for_context
from logic.ollama_client import OllamaClient, parse_icon_requests, strip_all_tokens
from logic.patch_context_store import PatchContextStore
from ui.itemizar_mode import ItemizarMode
from ui.model_manager_dialog import ModelManagerDialog


def test_infer_target_for_context_uses_champion_damage_type_when_meta_missing() -> None:
    meta = {"found": False, "full_build": []}
    champion_record = {
        "roles": ["MIDDLE"],
        "damage_type": ["AP"],
        "range_type": "RANGED",
    }

    target = infer_target_for_context(meta, {}, champion_record=champion_record, role="middle")

    assert target == OptimizationTarget.MAGIC_DPS


def test_infer_target_for_context_falls_back_to_role_default_when_no_tags() -> None:
    meta = {"found": False, "full_build": []}

    target = infer_target_for_context(meta, {}, champion_record={}, role="support")

    assert target == OptimizationTarget.UTILITY


def test_extract_meta_from_qdata_rebuilds_slot_based_build() -> None:
    objs = [None] * 40
    objs[0] = {
        "header": "1",
        "item1": "2",
        "boots": "3",
        "item2": "4",
        "item3": "5",
        "item4": "6",
        "item5": "7",
        "popularItem": "8",
    }
    objs[1] = {"wr": 52.4, "pr": 3.1}
    objs[2] = [["9", "a", "b", "c", "d"]]
    objs[3] = [["e", "f", "g", "h", "i"]]
    objs[4] = [["j", "k", "l", "m", "n"]]
    objs[5] = [["o", "p", "q", "r", "s"]]
    objs[6] = [["t", "u", "v", "w", "x"]]
    objs[7] = [["y", "z", "10", "11", "12"]]
    objs[8] = [["13", "14", "15", "16", "17"]]
    objs[9] = 3068
    objs[10] = 60.0
    objs[11] = 71.43
    objs[12] = 10
    objs[13] = 12
    objs[14] = 3047
    objs[15] = 50.0
    objs[16] = 42.86
    objs[17] = 6
    objs[18] = 13
    objs[19] = 3075
    objs[20] = 50.0
    objs[21] = 42.86
    objs[22] = 6
    objs[23] = 24
    objs[24] = 2502
    objs[25] = 50.0
    objs[26] = 35.0
    objs[27] = 5
    objs[28] = 27
    objs[29] = 6665
    objs[30] = 55.0
    objs[31] = 21.0
    objs[32] = 3
    objs[33] = 31
    objs[34] = 2525
    objs[35] = 66.67
    objs[36] = 14.29
    objs[37] = 2
    objs[38] = 38

    payload = {"_objs": objs}
    meta = _extract_meta_from_qdata(payload)

    assert meta["found"] is True
    assert meta["full_build"] == [3068, 3047, 3075, 2502, 6665, 2525]
    assert meta["core_items"] == [3068, 3075, 2502]
    assert meta["boots"] == 3047
    assert meta["winrate"] == 66.67
    assert meta["pickrate"] == 14.29
    assert meta["source"] == "lolalytics-qdata"


def test_extract_meta_from_qdata_accepts_partial_lane_builds_without_item4_and_item5() -> None:
    objs = [None] * 8
    objs[0] = {
        "header": "1",
        "item1": "2",
        "boots": "3",
        "item2": "4",
        "item3": "5",
        "popularItem": "6",
        "winningItem": "7",
    }
    objs[1] = {"wr": 30.77, "pr": 0.0}
    objs[2] = [[3146, 22.22, 69.23, 9, 13]]
    objs[3] = [[3020, 22.22, 69.23, 9, 14]]
    objs[4] = [[4645, 22.22, 69.23, 9, 21]]
    objs[5] = [[3089, 0.0, 7.69, 1, 23]]
    objs[6] = [[3157, 0.0, 23.08, 3, 25], [3100, 0.0, 15.38, 2, 12]]
    objs[7] = [[3157, 0.0, 23.08, 3, 25]]

    payload = {"_objs": objs}
    meta = _extract_meta_from_qdata(payload)

    assert meta["found"] is True
    assert meta["full_build"] == [3146, 3020, 4645, 3089, 3157, 3100]
    assert meta["boots"] == 3020
    assert meta["source"] == "lolalytics-qdata"
    assert meta["exact_lane"] is False


def test_extract_meta_from_qdata_prefers_requested_lane_when_multiple_candidates_exist() -> None:
    objs = [None] * 15
    objs[0] = {
        "header": "1",
        "item1": "2",
        "boots": "3",
        "item2": "4",
        "item3": "5",
        "item4": "6",
        "popularItem": "7",
    }
    objs[1] = {"lane": "top", "wr": 50.0, "pr": 2.0, "n": 100}
    objs[2] = [[6630, 52.0, 40.0, 10, 10]]
    objs[3] = [[3047, 52.0, 40.0, 10, 11]]
    objs[4] = [[3053, 52.0, 40.0, 10, 20]]
    objs[5] = [[3071, 52.0, 40.0, 10, 30]]
    objs[6] = [[6333, 52.0, 40.0, 10, 40]]
    objs[7] = [[3026, 52.0, 40.0, 10, 45]]
    objs[8] = {
        "header": "9",
        "item1": "a",
        "boots": "b",
        "item2": "c",
        "item3": "d",
        "popularItem": "e",
    }
    objs[9] = {"lane": "jungle", "wr": 60.0, "pr": 3.0, "n": 30}
    objs[10] = [[3146, 60.0, 50.0, 9, 10]]
    objs[11] = [[3020, 60.0, 50.0, 9, 12]]
    objs[12] = [[4645, 60.0, 50.0, 9, 20]]
    objs[13] = [[3089, 60.0, 50.0, 9, 28]]
    objs[14] = [[3157, 60.0, 50.0, 9, 32], [3100, 40.0, 10.0, 2, 18]]

    payload = {"_objs": objs}
    meta = _extract_meta_from_qdata(payload, requested_lane="jungle")

    assert meta["header_lane"] == "jungle"
    assert meta["exact_lane"] is True
    assert meta["full_build"] == [3146, 3020, 4645, 3089, 3157, 3100]


def test_build_champion_slug_uses_known_aliases() -> None:
    assert _build_champion_slug("Renata Glasc") == "renata"
    assert _build_champion_slug("Nunu & Willump") == "nunu"
    assert _build_champion_slug("Jarvan IV") == "jarvaniv"


def test_parse_icon_requests_deduplicates_and_preserves_order() -> None:
    text = "Usa IE y Conqueror [ICONS: ITEM:3031, RUNE:8010, ITEM:3031, RUNE:8010, ITEM:6673]"

    parsed = parse_icon_requests(text)

    assert parsed == [("ITEM", 3031), ("RUNE", 8010), ("ITEM", 6673)]


def test_strip_all_tokens_removes_build_and_icon_tokens() -> None:
    text = "Prueba [BUILD_REQUEST:{\"target\":\"PHYSICAL_DPS\"}] final [ICONS: ITEM:3031, RUNE:8010]"

    cleaned = strip_all_tokens(text)

    assert cleaned == "Prueba  final"


def test_knowledge_base_detects_entities_from_text() -> None:
    champions = {
        "Ahri": {"image_key": "Ahri"},
        "Rell": {"image_key": "Rell"},
    }
    kb = KnowledgeBase(champions)

    detected = kb.detect_entities("Para Ahri me gusta Infinity Edge con Electrocute.")

    assert "Ahri" in detected["champions"]
    assert isinstance(detected["items"], list)
    assert isinstance(detected["runes"], list)


def test_fetch_meta_build_falls_back_to_other_lane(monkeypatch) -> None:
    meta_build_fetcher._cache.clear()

    def fake_fetch(champion_slug: str, lane: str) -> dict:
        if lane == "jungle":
            raise ValueError("sin datos en jungle")
        if lane == "top":
            return {
                "core_items": [6630, 3047, 3053],
                "boots": 3047,
                "full_build": [6630, 3047, 3053, 3071, 6694, 6333],
                "winrate": 52.4,
                "pickrate": 4.1,
                "found": True,
                "source": "lolalytics-qdata",
                "error": "",
                "resolved_lane": lane,
            }
        raise ValueError(f"unexpected lane {lane}")

    monkeypatch.setattr(meta_build_fetcher, "_fetch_meta_for_lane", fake_fetch)

    result = meta_build_fetcher.fetch_meta_build("Aatrox", "jungle")

    assert result["found"] is True
    assert result["full_build"] == [6630, 3047, 3053, 3071, 6694, 6333]
    assert result["resolved_lane"] == "top"
    assert result["source"] == "lolalytics-qdata:fallback:top"
    assert result["error"] == ""


def test_cache_ttl_is_shorter_for_fallback_results() -> None:
    exact = {
        "resolved_lane": "jungle",
        "header_lane": "jungle",
    }
    fallback = {
        "resolved_lane": "top",
        "header_lane": "top",
    }

    assert meta_build_fetcher._cache_ttl_for_result(exact, "jungle") == meta_build_fetcher.CACHE_TTL
    assert meta_build_fetcher._cache_ttl_for_result(fallback, "jungle") == meta_build_fetcher.CACHE_TTL_FALLBACK


def test_http_get_json_ignores_broken_proxy_environment(monkeypatch) -> None:
    captured = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"ok": True}

    class _FakeSession:
        def __init__(self) -> None:
            self.trust_env = True

        def get(self, url: str, **kwargs):
            captured["trust_env"] = self.trust_env
            captured["url"] = url
            captured["kwargs"] = kwargs
            return _FakeResponse()

    monkeypatch.setattr(meta_build_fetcher.requests, "Session", _FakeSession)

    payload = meta_build_fetcher._http_get_json("https://example.com/test", params={"lane": "jungle"})

    assert payload == {"ok": True}
    assert captured["trust_env"] is False
    assert captured["kwargs"]["params"] == {"lane": "jungle"}


def test_fetch_meta_build_does_not_cache_failed_result(monkeypatch) -> None:
    meta_build_fetcher._cache.clear()
    calls = {"count": 0}

    def fake_fetch(champion_slug: str, lane: str) -> dict:
        calls["count"] += 1
        raise ValueError(f"fallo {lane}")

    monkeypatch.setattr(meta_build_fetcher, "_fetch_meta_for_lane", fake_fetch)

    first = meta_build_fetcher.fetch_meta_build("Rell", "jungle")
    second = meta_build_fetcher.fetch_meta_build("Rell", "jungle")

    assert first["found"] is False
    assert second["found"] is False
    assert calls["count"] == len(meta_build_fetcher._lane_candidates("jungle")) * 2
    assert "meta_rell_jungle" not in meta_build_fetcher._cache


class _FakePullResponse:
    def __init__(self, events: list[dict]) -> None:
        self._events = [json.dumps(event) for event in events]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = True):
        yield from self._events


def test_iter_pull_model_progress_reports_status_and_percentages() -> None:
    client = OllamaClient("http://localhost:11434")
    seen: list[tuple[str, int | None, int | None]] = []
    events = [
        {"status": "pulling manifest"},
        {"status": "downloading", "completed": 50, "total": 100},
        {"status": "success"},
    ]

    with patch.object(client, "ensure_server_ready", return_value=(True, "Ollama activo.")):
        with patch("logic.ollama_client.requests.post", return_value=_FakePullResponse(events)):
            parsed = list(client.iter_pull_model_progress("phi3:mini", callback=lambda s, c, t: seen.append((s, c, t))))

    assert [event["status"] for event in parsed] == ["pulling manifest", "downloading", "success"]
    assert seen[1] == ("downloading", 50, 100)


def test_prewarm_marks_model_as_ready_without_second_network_call() -> None:
    client = OllamaClient("http://localhost:11434")
    calls = {"count": 0}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"response": "OK"}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return _FakeResponse()

    with patch.object(client, "ensure_server_ready", return_value=(True, "Ollama activo.")):
        with patch("logic.ollama_client.requests.post", side_effect=fake_post):
            first = client.prewarm("phi3:mini")
            second = client.prewarm("phi3:mini")

    assert first == (True, "Modelo precalentado.")
    assert second == (True, "Modelo ya precalentado.")
    assert calls["count"] == 1


def test_generate_retries_after_first_read_timeout() -> None:
    client = OllamaClient("http://localhost:11434")
    calls = {"count": 0}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_lines(self, decode_unicode=True):
            yield json.dumps({"response": "Respuesta final", "done": False})
            yield json.dumps({"done": True})

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.exceptions.ReadTimeout("cold start")
        return _FakeResponse()

    with patch.object(client, "ensure_server_ready", return_value=(True, "Ollama activo.")):
        with patch("logic.ollama_client.requests.post", side_effect=fake_post):
            response = client.generate("phi3:mini", "hola")

    assert response == "Respuesta final"
    assert calls["count"] == 2


def test_connection_status_reports_not_installed(monkeypatch) -> None:
    client = OllamaClient("http://localhost:11434")
    monkeypatch.setattr(client, "is_server_running", lambda: False)
    monkeypatch.setattr(client, "find_local_executable", lambda: None)

    ok, message = client.connection_status()

    assert ok is False
    assert "no está instalado" in message.lower()


def test_iter_pull_model_progress_raises_clear_error_when_ollama_missing(monkeypatch) -> None:
    client = OllamaClient("http://localhost:11434")
    monkeypatch.setattr(client, "ensure_server_ready", lambda autostart=True: (False, "Ollama no está instalado en este equipo."))

    try:
        list(client.iter_pull_model_progress("gemma2:2b"))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "no está instalado" in str(exc).lower()


def test_model_manager_use_accepts_dialog(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(OllamaClient, "recommended_models", lambda self: [])
    monkeypatch.setattr(OllamaClient, "list_models", lambda self: [])
    monkeypatch.setattr(OllamaClient, "connection_status", lambda self: (True, "Ollama activo."))
    dialog = ModelManagerDialog(selected_model="", parent=None)

    try:
        dialog._use_model("qwen2.5:1.5b")
        assert dialog.selected_model == "qwen2.5:1.5b"
        assert dialog.result() == dialog.DialogCode.Accepted
    finally:
        dialog.close()


class _DummyLoader:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir


def _build_itemizar_mode_for_chat(monkeypatch) -> ItemizarMode:
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ItemizarMode, "_populate_controls", lambda self: None)
    monkeypatch.setattr(ItemizarMode, "_detect_models", lambda self: None)
    monkeypatch.setattr(ItemizarMode, "_ensure_knowledge_base", lambda self, force_refresh=False: None)
    mode = ItemizarMode(
        {"Rell": {"image_key": "Rell", "roles": ["JUNGLE"], "ability_tags": ["HARD_ENGAGE"]}},
        _DummyLoader(str(PROJECT_ROOT)),
        data_meta={"current_patch": "16.12.1"},
    )
    mode.selected_model = "phi3:mini"
    mode.selected_champ = "Rell"
    mode.selected_role = "jungle"
    mode.current_patch = "16.12.1"
    mode.current_meta = {
        "found": True,
        "resolved_lane": "jungle",
        "full_build": [3068, 3047],
        "winrate": 51.2,
        "pickrate": 3.4,
    }
    mode.current_items = {
        3068: {"id": 3068, "name": "Sunfire Aegis"},
        3047: {"id": 3047, "name": "Plated Steelcaps"},
    }
    mode.current_runes = {}
    mode.current_rune_entries = {}
    mode.knowledge_base = type(
        "_FakeKB",
        (),
        {
            "get_champion_kit_summary": lambda self, champion: "Rell tiene engage fuerte y CC en area.",
            "detect_entities": lambda self, text: {"champions": [], "items": [], "runes": []},
            "build_context_block": lambda self, detected, current_champion="": "",
        },
    )()
    mode._test_app = app
    return mode


def _install_stream_reply(monkeypatch, mode: ItemizarMode, reply: str, capture: dict | None = None) -> dict:
    state = {"calls": 0}

    def fake_stream_generate(*args, **kwargs):
        state["calls"] += 1
        if capture is not None:
            capture["kwargs"] = kwargs
        callback = kwargs.get("callback")
        if callback:
            midpoint = max(1, len(reply) // 2)
            partial = ""
            for chunk in (reply[:midpoint], reply[midpoint:]):
                if not chunk:
                    continue
                partial += chunk
                callback(partial)
        return reply

    monkeypatch.setattr(mode.ollama_client, "stream_generate", fake_stream_generate)
    return state


def _wait_for_text(mode: ItemizarMode, expected: str, timeout_seconds: float = 5.0) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        mode._test_app.processEvents()
        chat_text = mode.chat_log.toPlainText()
        if expected in chat_text:
            return chat_text
        time.sleep(0.01)
    return mode.chat_log.toPlainText()


def test_itemizar_chat_unknown_question_uses_llm_when_not_handled_locally(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    called = _install_stream_reply(monkeypatch, mode, "Respuesta realista del modelo")
    mode.chat_input.setText("Que sinergias generales ves para Rell jungla con esta build?")

    try:
        mode._send_chat()
        chat_text = _wait_for_text(mode, "Respuesta realista del modelo")
        assert "Respuesta realista del modelo" in chat_text
        assert called["calls"] == 1
    finally:
        mode.close()


def test_itemizar_chat_utility_request_uses_local_constraints_without_llm(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    called = {"optimize": 0}

    def fake_optimize(constraints: dict) -> None:
        called["optimize"] += 1
        mode.current_constraints = constraints

    _install_stream_reply(
        monkeypatch,
        mode,
        'He aplicado tu peticion al optimizador y voy a recalcular la build. [BUILD_REQUEST:{"target":"UTILITY"}]',
    )
    monkeypatch.setattr(mode, "_start_optimization_with_constraints", fake_optimize)
    mode.chat_input.setText("Quiero una build mas utilitaria.")

    try:
        mode._send_chat()
        chat_text = _wait_for_text(mode, "He aplicado tu peticion al optimizador")
        deadline = time.time() + 2
        while time.time() < deadline and called["optimize"] == 0:
            mode._test_app.processEvents()
            time.sleep(0.01)
        assert "He aplicado tu peticion al optimizador" in chat_text
        assert called["optimize"] == 1
        assert mode.current_constraints == {"target": "UTILITY"}
    finally:
        mode.close()


def test_itemizar_chat_greeting_answers_normally(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    called = _install_stream_reply(monkeypatch, mode, "Si, te recibo bien.")

    try:
        mode.chat_input.setText("me recibes?")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "Si, te recibo bien.").lower()
        assert "te recibo bien" in chat_text
        assert called["calls"] == 1
    finally:
        mode.close()


def test_itemizar_chat_how_is_the_build_answers_without_reoptimization(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    called = _install_stream_reply(
        monkeypatch,
        mode,
        "La build meta actual de Rell JUNGLE es Sunfire Aegis y Plated Steelcaps. Tiene sentido porque prioriza engage y frontline.",
    )

    try:
        mode.chat_input.setText("como ves la build")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "La build meta actual de Rell JUNGLE es")
        assert "La build meta actual de Rell JUNGLE es" in chat_text
        assert "Tiene sentido porque" in chat_text
        assert "Restricciones detectadas" not in chat_text
        assert called["calls"] == 1
    finally:
        mode.close()


def test_itemizar_chat_ignores_build_request_token_when_user_did_not_ask_for_changes(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    _install_stream_reply(monkeypatch, mode, '[BUILD_REQUEST:{"target":"PHYSICAL_DPS","force_items":[3031]}]')

    try:
        mode.chat_input.setText("que opinas de esta build?")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "No he podido construir una respuesta util")
        assert "Restricciones detectadas" not in chat_text
        assert "He aplicado tu peticion al optimizador" not in chat_text
    finally:
        mode.close()


def test_itemizar_chat_ap_damage_opinion_does_not_trigger_reoptimization(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    called = _install_stream_reply(monkeypatch, mode, "La build tiene mas peso de frontline y utilidad que de dano AP.")

    try:
        mode.chat_input.setText("no crees que le falta daño ap?")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "frontline y utilidad").lower()
        assert "frontline y utilidad" in chat_text
        assert "Restricciones detectadas" not in chat_text
        assert called["calls"] == 1
    finally:
        mode.close()


def test_itemizar_chat_other_champion_scope_reply_is_normal(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    mode.champion_pool["Nafiri"] = {"image_key": "Nafiri", "roles": ["MIDDLE", "JUNGLE"]}
    called = _install_stream_reply(monkeypatch, mode, "Si quieres afinar runas de Naafiri, cambia el campeon activo y lo vemos.")

    try:
        mode.chat_input.setText("en una compo x que runas encajan mejor en nafiri?")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "cambia el campeon activo")
        assert "cambia el campeon activo" in chat_text.lower()
        assert called["calls"] == 1
    finally:
        mode.close()


def test_itemizar_chat_build_overview_phrase_answers_normally(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    called = _install_stream_reply(monkeypatch, mode, "La build meta actual de Rell JUNGLE es Sunfire Aegis y Plated Steelcaps.")

    try:
        mode.chat_input.setText("como ves la build")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "La build meta actual de Rell JUNGLE es")
        assert "La build meta actual de Rell JUNGLE es" in chat_text
        assert "Restricciones detectadas" not in chat_text
        assert called["calls"] == 1
    finally:
        mode.close()


def test_itemizar_chat_matchup_advantage_uses_meta_data(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    mode.champion_pool["Fizz"] = {"roles": ["MIDDLE"]}
    mode.champion_pool["Vladimir"] = {"roles": ["MIDDLE", "TOP"]}
    capture: dict = {}

    def fake_fetch_matchup_data(champion: str, lane: str) -> dict:
        if champion == "Vladimir" and lane == "middle":
            return {"counters": [{"id": "Fizz", "winrate": 52.3, "games": 1200}], "best_build": [], "start_items": []}
        return {"counters": [], "best_build": [], "start_items": []}

    monkeypatch.setattr("ui.itemizar_mode.fetch_matchup_data", fake_fetch_matchup_data)
    _install_stream_reply(monkeypatch, mode, "Vladimir tiene una ligera ventaja en el matchup.", capture=capture)

    try:
        mode.chat_input.setText("quien tiene la ventaja en el matchup fizz vs vladimir?")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "Vladimir tiene una ligera ventaja")
        assert "Vladimir tiene una ligera ventaja" in chat_text
        dynamic_context = str(capture["kwargs"]["dynamic_context"])
        assert "MATCHUP META" in dynamic_context
        assert "Fizz (52.3%)" in dynamic_context
    finally:
        mode.close()


def test_itemizar_chat_best_pick_against_uses_meta_data(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    mode.champion_pool["Teemo"] = {"roles": ["TOP", "JUNGLE"]}
    capture: dict = {}

    def fake_fetch_matchup_data(champion: str, lane: str) -> dict:
        if champion == "Teemo" and lane == "top":
            return {"counters": [{"id": "Malphite", "winrate": 54.9, "games": 900}], "best_build": [], "start_items": []}
        return {"counters": [], "best_build": [], "start_items": []}

    monkeypatch.setattr("ui.itemizar_mode.fetch_matchup_data", fake_fetch_matchup_data)
    _install_stream_reply(monkeypatch, mode, "Malphite es el mejor pick contra Teemo en top.", capture=capture)

    try:
        mode.chat_input.setText("cual es el mejor pick contra teemo?")
        mode._send_chat()
        chat_text = _wait_for_text(mode, "Malphite es el mejor pick")
        assert "Malphite es el mejor pick" in chat_text
        dynamic_context = str(capture["kwargs"]["dynamic_context"])
        assert "COUNTERS META" in dynamic_context
        assert "Malphite (54.9%)" in dynamic_context
    finally:
        mode.close()


def test_itemizar_chat_centers_item_and_rune_icons(monkeypatch) -> None:
    mode = _build_itemizar_mode_for_chat(monkeypatch)
    mode.current_rune_entries = {8008: {"id": 8008, "name": "Lethal Tempo", "slot": 0}}
    mode.knowledge_base = type("_FakeKBIcons", (), {"runes": {8008: {"name": "Lethal Tempo", "slot": 0}}})()
    fake_icon_path = Path(__file__)
    monkeypatch.setattr(mode.item_loader, "get_item_icon_path", lambda item_id, version: fake_icon_path)
    monkeypatch.setattr(mode.rune_loader, "get_rune_icon_path", lambda rune_id, version: fake_icon_path)

    try:
        html_block = mode._build_icon_block_html([("ITEM", 3068), ("RUNE", 8008)])
        assert "text-align:center" in html_block
        assert "Sunfire Aegis" in html_block
        assert "Lethal Tempo" in html_block
    finally:
        mode.close()


def test_patch_context_store_generates_compact_snapshot(monkeypatch) -> None:
    class _FakeItemLoader:
        def load_items(self, version: str, force_refresh: bool = False) -> dict[int, dict]:
            return {
                3068: {"name": "Sunfire Aegis"},
                3047: {"name": "Plated Steelcaps"},
            }

    class _FakeRuneLoader:
        def load_runes(self, version: str, force_refresh: bool = False) -> dict[int, dict]:
            return {
                8008: {"name": "Lethal Tempo", "tree": "Precision"},
                8100: {"name": "Domination", "tree": "Domination"},
            }

    monkeypatch.setattr(
        "logic.patch_context_store.fetch_tier_list",
        lambda role: [{"id": "Rell", "tier": "B", "rank": 14, "winrate": 51.2, "pickrate": 3.4}],
    )
    tmp_path = PROJECT_ROOT / "tmp_test_patch_context_snapshot"
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = PatchContextStore(
        tmp_path,
        {"Rell": {"roles": ["JUNGLE"]}, "Teemo": {"roles": ["TOP"]}},
        _FakeItemLoader(),
        _FakeRuneLoader(),
    )

    payload = store.ensure_patch_snapshot("16.12.1", force_refresh=True)

    assert payload["version"] == "16.12.1"
    assert "prompt_min" in payload
    assert "JGL: Rell(B,51.2% WR)." in payload["prompt_min"]
    assert payload["item_aliases"]["sunfireaegis"] == 3068
    assert payload["rune_aliases"]["lethaltempo"] == 8008


def test_patch_context_store_writes_champion_context() -> None:
    class _FakeItemLoader:
        def load_items(self, version: str, force_refresh: bool = False) -> dict[int, dict]:
            return {}

    class _FakeRuneLoader:
        def load_runes(self, version: str, force_refresh: bool = False) -> dict[int, dict]:
            return {}

    tmp_path = PROJECT_ROOT / "tmp_test_patch_context_champion"
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = PatchContextStore(
        tmp_path,
        {"Rell": {"roles": ["JUNGLE"]}},
        _FakeItemLoader(),
        _FakeRuneLoader(),
    )

    payload = store.write_champion_context(
        version="16.12.1",
        champion="Rell",
        role="jungle",
        current_meta={"full_build": [3068, 3047], "found": True, "winrate": 51.2, "pickrate": 3.4},
        current_runes={"primary_runes": [8008], "secondary_runes": [8105], "stat_shards": [5008]},
        current_items={3068: {"name": "Sunfire Aegis"}, 3047: {"name": "Plated Steelcaps"}},
        rune_entries={
            8008: {"name": "Lethal Tempo"},
            8105: {"name": "Treasure Hunter"},
            5008: {"name": "Adaptive Force"},
        },
        champion_record={"ability_tags": ["HARD_ENGAGE"], "countered_by": ["Poppy"], "archetype_fit": {"Pick Comp": 0.8}},
    )

    assert payload["meta_build_names"] == ["Sunfire Aegis", "Plated Steelcaps"]
    prompt = store.get_champion_prompt("Rell", "jungle")
    assert "Campeon activo: Rell JGL." in prompt
    assert "Sunfire Aegis > Plated Steelcaps" in prompt
