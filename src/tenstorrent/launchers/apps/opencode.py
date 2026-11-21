# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025-2026 Tenstorrent USA, Inc.

"""OpenCode adapter: an openai-compatible provider block named `tenstorrent`."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

from ...errors import TTError
from ..base import (
    ConfigChange,
    LaunchEnv,
    LaunchOptions,
    Preparation,
    RunningModel,
    config_consent,
    json_config_drop,
    json_config_has,
    output_budget,
    read_json_config,
    user_config_dir,
    write_json_config,
)

PROVIDER_KEY = "tenstorrent"
_SCHEMA = "https://opencode.ai/config.json"
# The provider schema wants a key; models tt serves are unauthenticated and ignore it.
_PLACEHOLDER_KEY = "tt-local"
# OpenCode 2 dropped the top-level `--model` flag (it survives on `opencode run`), and the
# model is now chosen by config. Inline config in this variable applies to one run, wins
# over a `model` key in the user's own file, and leaves that file alone.
_INLINE_CONFIG_ENV = "OPENCODE_CONFIG_CONTENT"
_VERSION_TIMEOUT_S = 10
# First `N.N.N` in the output: OpenCode 1 prints `1.19.6`, OpenCode 2 prints `opencode v2.3.2`.
_VERSION_RE = re.compile(r"(\d+)\.\d+\.\d+")


class OpenCode:
    id = "opencode"
    binaries = ("opencode",)
    install_hint = "Install OpenCode (https://opencode.ai/docs/), then re-run."
    requires_tool_calling = True
    hands_over_terminal = True

    def config_path(self) -> Path:
        return user_config_dir() / "opencode" / "opencode.json"

    def target(self) -> str:
        return str(self.config_path())

    def plan(
        self,
        model: RunningModel,
        options: LaunchOptions,
        *,
        executable: str | None,
        runner,
    ) -> Preparation:
        path = self.config_path()
        major = self._major_version(executable, runner)
        doc, created = read_json_config(path)
        # Snapshot before mutating: setdefault hands back the live dict, and the
        # comparison below decides whether the user is asked at all.
        before = deepcopy(doc.get("provider", {}).get(PROVIDER_KEY))
        provider = doc.setdefault("provider", {}).setdefault(PROVIDER_KEY, {})
        provider.update(
            {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Tenstorrent",
                "options": {"baseURL": model.base_url, "apiKey": _PLACEHOLDER_KEY},
            }
        )
        # Merge rather than replace: a model configured by an earlier launch stays
        # selectable in OpenCode's own picker.
        provider.setdefault("models", {})[model.served_id] = self._model_entry(model)
        if created:
            doc.setdefault("$schema", _SCHEMA)
        return Preparation(
            config=ConfigChange(
                path=path,
                key=f"provider.{PROVIDER_KEY}",
                block=provider,
                document=doc,
                created=created,
            ),
            # Nothing to approve when the entry is already exactly this.
            consent=None
            if before == provider
            else config_consent(path, f"provider.{PROVIDER_KEY}", existing=before),
            steps=[self._argv(executable or self.binaries[0], model, major)],
            env=self._env(model, major),
        )

    def apply(self, model: RunningModel, prep: Preparation, env: LaunchEnv) -> None:
        assert prep.config is not None
        write_json_config(prep.config.path, prep.config.document)

    def handoff(self, model: RunningModel, prep: Preparation, env: LaunchEnv) -> None:
        # What plan() decided (flag or environment, by version), at the path the client was found.
        argv = [env.executable, *prep.steps[0][1:]]
        env.runner.exec_tty(argv, env=prep.env)

    def disconnect_plan(self, executable: str | None, runner) -> str | None:
        path = self.config_path()
        if not json_config_has(path, ("provider",), PROVIDER_KEY):
            return None
        return f"remove provider.{PROVIDER_KEY} from {path}"

    def disconnect(self, env: LaunchEnv) -> None:
        json_config_drop(self.config_path(), ("provider",), PROVIDER_KEY)

    def _model_entry(self, model: RunningModel) -> dict:
        entry = {"name": model.served_id}
        # Without a limit it requests 32000 output tokens whatever the window.
        if model.max_context:
            entry["limit"] = {
                "context": model.max_context,
                "output": output_budget(model.max_context),
            }
        return entry

    def _major_version(self, executable: str | None, runner) -> int | None:
        """The client's major version, or None when it cannot be read.

        Unreadable means the old behavior (`--model`), so a dry run before the client is
        installed, a client that prints nothing, and a failing `--version` all plan what
        earlier releases planned.
        """
        if not executable or runner is None:
            return None
        try:
            result = runner.capture(
                [executable, "--version"], timeout=_VERSION_TIMEOUT_S, check=False
            )
        except TTError:
            return None
        if result.returncode != 0:
            return None
        match = _VERSION_RE.search(result.stdout or "")
        return int(match.group(1)) if match else None

    def _model_ref(self, model: RunningModel) -> str:
        # served_id is whatever the API expects, so a repo-shaped id makes a ref
        # with two slashes (tenstorrent/Qwen/Qwen3-32B). Correctness with the
        # server wins: a shortened key would be sent verbatim and 404.
        return f"{PROVIDER_KEY}/{model.served_id}"

    def _argv(
        self, executable: str, model: RunningModel, major: int | None
    ) -> list[str]:
        if major is not None and major >= 2:
            return [executable]
        return [executable, "--model", self._model_ref(model)]

    def _env(self, model: RunningModel, major: int | None) -> dict:
        if major is None or major < 2:
            return {}
        return {_INLINE_CONFIG_ENV: json.dumps({"model": self._model_ref(model)})}
