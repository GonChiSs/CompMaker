from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable

import requests

OLLAMA_BASE_URL = "http://localhost:11434"
REQUEST_TIMEOUT = 45
GENERATE_TIMEOUT = (10, 120)
PREWARM_TIMEOUT = (10, 90)
GENERATE_RETRY_DELAY_SECONDS = 1.5
MAX_HISTORY_MESSAGES = 4
BUILD_REQUEST_RE = re.compile(r"\[(?:BUILD_REQUEST|TARGET_BUILD):\s*(\{.*?\})\s*\]", re.DOTALL)
ICON_REQUEST_PATTERN = re.compile(r"\[ICONS:\s*([^\]]+)\]")
ALL_TOKENS_PATTERN = re.compile(r"\[(?:BUILD_REQUEST|TARGET_BUILD):[^\]]*\]|\[ICONS:[^\]]*\]", re.DOTALL)
JSON_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)
RECOMMENDED_MODELS = [
    {
        "id": "phi3:mini",
        "label": "Phi-3 Mini",
        "params": "3.8B",
        "size": "2.3 GB",
        "ram": "~4 GB RAM",
        "desc": "Mejor equilibrio calidad/recursos. Recomendado por defecto.",
        "speed": "Rapido",
        "quality": "★★★★☆",
    },
    {
        "id": "gemma2:2b",
        "label": "Gemma 2",
        "params": "2B",
        "size": "1.6 GB",
        "ram": "~3 GB RAM",
        "desc": "Muy ligero, ideal para portatiles modestos.",
        "speed": "Muy rapido",
        "quality": "★★★☆☆",
    },
    {
        "id": "llama3.2:3b",
        "label": "Llama 3.2",
        "params": "3B",
        "size": "2.0 GB",
        "ram": "~4 GB RAM",
        "desc": "Buena comprension de contexto y conversacion natural.",
        "speed": "Rapido",
        "quality": "★★★★☆",
    },
    {
        "id": "qwen2.5:1.5b",
        "label": "Qwen 2.5",
        "params": "1.5B",
        "size": "1.0 GB",
        "ram": "~2 GB RAM",
        "desc": "El mas compacto. Para PCs con recursos muy limitados.",
        "speed": "Muy rapido",
        "quality": "★★★☆☆",
    },
    {
        "id": "mistral:7b",
        "label": "Mistral",
        "params": "7B",
        "size": "4.1 GB",
        "ram": "~8 GB RAM",
        "desc": "Mayor calidad de razonamiento. Requiere PC mas potente.",
        "speed": "Moderado",
        "quality": "★★★★★",
    },
]

def parse_icon_requests(text: str) -> list[tuple[str, int]]:
    results: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for match in ICON_REQUEST_PATTERN.finditer(text or ""):
        for part in match.group(1).split(","):
            chunk = str(part).strip()
            if ":" not in chunk:
                continue
            kind, _, id_str = chunk.partition(":")
            try:
                entity_id = int(id_str.strip())
            except ValueError:
                continue
            key = (kind.strip().upper(), entity_id)
            if key[0] in {"ITEM", "RUNE"} and key not in seen:
                results.append(key)
                seen.add(key)
    return results


def strip_all_tokens(text: str) -> str:
    return ALL_TOKENS_PATTERN.sub("", text or "").strip()


def make_system_prompt(
    champion_name: str,
    role: str,
    current_build: list[dict],
    all_items: dict,
    optimization_target: str,
    patch_version: str = "",
) -> str:
    item_names = ", ".join(f"{item.get('name', '-') } (ID {item.get('id', 0)})" for item in current_build) or "sin items visibles"
    opt_label = {
        "PHYSICAL_DPS": "DPS fisico",
        "MAGIC_DPS": "DPS magico",
        "TANK_HP": "tanque HP",
        "UTILITY": "utilidad",
        "LETHALITY": "letalidad/asesino",
        "LIFESTEAL_DPS": "DPS con robo de vida",
        "TANK_ARMOR": "tanque fisico",
        "TANK_MR": "tanque magico",
        "HYBRID_DPS": "DPS hibrido",
        "GOLD_EFFICIENCY": "eficiencia de oro",
    }.get(optimization_target, optimization_target)
    optimization_options = (
        "PHYSICAL_DPS, MAGIC_DPS, HYBRID_DPS, TANK_HP, TANK_ARMOR, "
        "TANK_MR, UTILITY, GOLD_EFFICIENCY, LETHALITY, LIFESTEAL_DPS"
    )
    return (
        f"Eres Comp AI, un asistente experto de League of Legends especializado en builds, runas, matchups y contexto de partida, "
        f"con conocimiento ACTUALIZADO al parche {patch_version or 'actual'}.\n\n"
        f"El usuario juega {champion_name} en el rol {role.upper()}.\n"
        f"La build actual (optimizacion: {opt_label}) es: {item_names}.\n\n"
        "Habla de forma natural, util y directa, como una IA conversacional moderna. "
        "Tienes libertad total en el estilo de la respuesta: puedes opinar, comparar opciones, proponer alternativas y razonar paso a paso si aporta valor.\n\n"
        "=== PROTOCOLO DE ICONOS ===\n"
        "Cuando tu respuesta mencione items o runas ESPECIFICOS por nombre o ID, termina tu respuesta con:\n"
        "[ICONS: ITEM:id1, ITEM:id2, RUNE:id3, RUNE:id4]\n"
        "Usa SOLO IDs numericos que aparezcan en el contexto del parche. No inventes IDs. "
        "Incluye todos los items/runas relevantes que mencionaste, hasta 6 en total. "
        "Si no mencionas ninguno, no incluyas el token.\n\n"
        "=== PROTOCOLO DE BUILD ===\n"
        "Cuando el usuario pida una build alternativa o con enfoque diferente, incluye al final:\n"
        "[BUILD_REQUEST:{\"target\":\"PHYSICAL_DPS\",\"force_items\":[3031],\"exclude_items\":[3078],"
        "\"min_hp\":0,\"prefer_tags\":[\"Damage\"]}]\n"
        f"Targets disponibles: {optimization_options}\n"
        "Usa solo JSON valido dentro del token. "
        "Elige target coherente con el campeon y la peticion: magos/AP -> MAGIC_DPS salvo que pidan tanque, "
        "ADC/AD -> PHYSICAL_DPS, builds defensivas -> TANK_HP/TANK_ARMOR/TANK_MR, supports utilitarios -> UTILITY.\n"
        "Responde siempre en espanol. Prioriza la informacion de meta y parche recibida en el contexto; si algo no esta verificado, indicalo como inferencia o duda razonable en vez de presentarlo como un hecho.\n"
        "Si el usuario pide responder exactamente con una palabra, una frase o un formato concreto, obedecelo literalmente y no anadas texto extra.\n"
        "Si te faltan datos exactos para cifras de meta o matchup, evita inventar porcentajes concretos. "
        "Puedes responder con criterio general de League of Legends siempre que dejes claro cuando estas interpretando o extrapolando."
    )


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._prewarmed_models: set[str] = set()

    def _health_url(self) -> str:
        return f"{self.base_url}/api/tags"

    def is_server_running(self) -> bool:
        try:
            response = requests.get(self._health_url(), timeout=3)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def find_local_executable(self) -> str | None:
        candidate = shutil.which("ollama")
        if candidate:
            return candidate

        local_appdata = os.getenv("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe"),
            os.path.join(local_appdata, "Programs", "Ollama", "ollama app.exe"),
            r"C:\Program Files\Ollama\ollama.exe",
            r"C:\Program Files\Ollama\ollama app.exe",
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def ensure_server_ready(self, autostart: bool = True) -> tuple[bool, str]:
        if self.is_server_running():
            return True, "Ollama activo."

        executable = self.find_local_executable()
        if executable is None:
            return False, "Ollama no está instalado en este equipo."
        if not autostart:
            return False, "Ollama está instalado, pero su servicio local no está iniciado."

        try:
            exe_name = os.path.basename(executable).lower()
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL,
                "creationflags": creation_flags,
            }
            if "app.exe" in exe_name:
                subprocess.Popen([executable], **kwargs)
            else:
                subprocess.Popen([executable, "serve"], **kwargs)
        except Exception as exc:
            return False, f"No se pudo iniciar Ollama automáticamente: {exc}"

        deadline = time.time() + 8.0
        while time.time() < deadline:
            if self.is_server_running():
                return True, "Ollama iniciado automáticamente."
            time.sleep(0.5)
        return False, "Ollama está instalado, pero no respondió al intentar iniciarlo."

    def connection_status(self) -> tuple[bool, str]:
        ok, message = self.ensure_server_ready(autostart=False)
        return ok, message

    def list_models(self) -> list[str]:
        try:
            response = requests.get(self._health_url(), timeout=8)
            response.raise_for_status()
            payload = response.json()
            models = payload.get("models", [])
            return [str(model.get("name", "")).strip() for model in models if model.get("name")]
        except Exception:
            return []

    def recommended_models(self) -> list[dict]:
        installed = set(self.list_models())
        result = []
        for config in RECOMMENDED_MODELS:
            result.append({**config, "installed": config["id"] in installed})
        return result

    def pull_model(self, model_id: str) -> bool:
        for _ in self.iter_pull_model_progress(model_id):
            pass
        return True

    def iter_pull_model_progress(
        self,
        model_id: str,
        callback: Callable[[str, int | None, int | None], None] | None = None,
    ):
        ok, message = self.ensure_server_ready(autostart=True)
        if not ok:
            raise RuntimeError(message)
        with requests.post(
            f"{self.base_url}/api/pull",
            json={"name": model_id, "stream": True},
            timeout=(10, 60),
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                event = json.loads(raw_line)
                status = str(event.get("status", "")).strip() or "Descargando"
                completed = event.get("completed")
                total = event.get("total")
                completed_value = int(completed) if isinstance(completed, (int, float)) else None
                total_value = int(total) if isinstance(total, (int, float)) else None
                if callback is not None:
                    callback(status, completed_value, total_value)
                yield {
                    "status": status,
                    "completed": completed_value,
                    "total": total_value,
                    "digest": str(event.get("digest", "")).strip(),
                }

    def delete_model(self, model_id: str) -> bool:
        response = requests.delete(
            f"{self.base_url}/api/delete",
            json={"name": model_id},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return True

    def generate(
        self,
        model: str,
        prompt: str,
        context: dict | None = None,
        system_prompt: str = "",
        history: list[dict] | None = None,
        dynamic_context: str = "",
    ) -> str:
        return self.stream_generate(
            model=model,
            prompt=prompt,
            context=context,
            system_prompt=system_prompt,
            history=history,
            dynamic_context=dynamic_context,
        )

    def stream_generate(
        self,
        model: str,
        prompt: str,
        context: dict | None = None,
        system_prompt: str = "",
        history: list[dict] | None = None,
        dynamic_context: str = "",
        callback: Callable[[str], None] | None = None,
    ) -> str:
        payload = {
            "model": model,
            "prompt": self._compose_prompt(
                prompt,
                context or {},
                system_prompt=system_prompt,
                history=history or [],
                dynamic_context=dynamic_context,
            ),
            "stream": True,
            "keep_alive": "30m",
        }
        ok, message = self.ensure_server_ready(autostart=True)
        if not ok:
            raise RuntimeError(message)

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                parts: list[str] = []
                with requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=GENERATE_TIMEOUT,
                    stream=True,
                ) as response:
                    response.raise_for_status()
                    for raw_line in response.iter_lines(decode_unicode=True):
                        if not raw_line:
                            continue
                        event = json.loads(raw_line)
                        chunk = str(event.get("response", "") or "")
                        if chunk:
                            parts.append(chunk)
                            if callback is not None:
                                callback("".join(parts))
                        if event.get("done"):
                            break
                return "".join(parts).strip()
            except requests.exceptions.ReadTimeout as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(GENERATE_RETRY_DELAY_SECONDS)
                    continue
                raise RuntimeError(
                    "Comp AI tardó demasiado en responder. Ollama se inició, pero el modelo no terminó de cargar a tiempo."
                ) from exc
            except Exception as exc:
                last_error = exc
                break

        if last_error is not None:
            raise last_error
        raise RuntimeError("No se pudo obtener respuesta de Comp AI.")

    def prewarm(self, model: str) -> tuple[bool, str]:
        model_name = str(model or "").strip()
        if not model_name:
            return False, "Sin modelo para precalentar."
        if model_name in self._prewarmed_models:
            return True, "Modelo ya precalentado."

        ok, message = self.ensure_server_ready(autostart=True)
        if not ok:
            return False, message

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Responde solo: OK",
                    "stream": False,
                    "options": {"num_predict": 1},
                },
                timeout=PREWARM_TIMEOUT,
            )
            response.raise_for_status()
            self._prewarmed_models.add(model_name)
            return True, "Modelo precalentado."
        except Exception as exc:
            return False, f"No se pudo precalentar el modelo: {exc}"

    def _compose_prompt(
        self,
        prompt: str,
        context: dict,
        system_prompt: str = "",
        history: list[dict] | None = None,
        dynamic_context: str = "",
    ) -> str:
        context_json = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
        transcript_lines: list[str] = []
        for message in (history or [])[-MAX_HISTORY_MESSAGES:]:
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                transcript_lines.append(f"Usuario: {content}")
            elif role == "assistant":
                transcript_lines.append(f"Asistente: {content}")
        transcript = "\n".join(transcript_lines).strip()
        dynamic_block = f"\n\n{dynamic_context}" if dynamic_context else ""
        transcript_block = f"\n\nHistorial reciente:\n{transcript}" if transcript else ""
        system_block = system_prompt.strip()
        return f"{system_block}{dynamic_block}\n\nContexto actual:\n{context_json}{transcript_block}\n\nUsuario:\n{prompt}"

    @staticmethod
    def extract_build_request(message: str) -> tuple[str, dict | None]:
        match = BUILD_REQUEST_RE.search(message or "")
        if match:
            token = match.group(0)
            json_payload = match.group(1)
            cleaned_message = strip_all_tokens((message or "").replace(token, "").strip())
            try:
                constraints = json.loads(json_payload)
                if isinstance(constraints, dict):
                    return cleaned_message, constraints
            except Exception:
                return cleaned_message, None
            return cleaned_message, None

        fallback_match = JSON_OBJECT_RE.search(message or "")
        cleaned_message = strip_all_tokens(message or "")
        if not fallback_match:
            return cleaned_message, None

        json_payload = fallback_match.group(1)
        try:
            constraints = json.loads(json_payload)
        except Exception:
            return cleaned_message, None
        if not isinstance(constraints, dict):
            return cleaned_message, None

        known_keys = {"target", "force_items", "exclude_items", "min_hp", "prefer_tags"}
        if not (known_keys & set(constraints.keys())):
            return cleaned_message, None

        cleaned_without_json = cleaned_message.replace(json_payload, "").strip()
        cleaned_without_json = (
            cleaned_without_json
            .replace("[TOKEN_REQUEST]", "")
            .replace("[TOKEN_BUILD_REQUEST]", "")
            .strip()
        )
        return cleaned_without_json, constraints
