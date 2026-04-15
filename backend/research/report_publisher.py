import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


def _load_workspace_dotenv(base_dir: Path) -> dict[str, str]:
    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_config_value(name: str, dotenv_values: dict[str, str], default: str = "") -> str:
    if name in os.environ:
        return os.environ[name]
    if name in dotenv_values:
        return dotenv_values[name]
    return default


@dataclass
class VercelPublishConfig:
    token: str = ""
    project_dir: str = "outputs/dingtalk_reports"
    scope: str = ""

    @classmethod
    def from_env(cls, base_dir: Path | None = None):
        dotenv_values = _load_workspace_dotenv(base_dir or Path.cwd())
        return cls(
            token=_get_config_value("VERCEL_TOKEN", dotenv_values, ""),
            project_dir=_get_config_value("VERCEL_PROJECT_DIR", dotenv_values, "outputs/dingtalk_reports"),
            scope=_get_config_value("VERCEL_SCOPE", dotenv_values, ""),
        )


class VercelStaticPublisher:
    def __init__(
        self,
        config: VercelPublishConfig | None = None,
        base_dir: Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
    ):
        self.base_dir = base_dir or Path.cwd()
        self.config = config or VercelPublishConfig.from_env(self.base_dir)
        self.runner = runner or subprocess.run
        self.is_configured = bool(self.config.token)

    def publish_report(self, html_report_path: Path | str) -> dict:
        html_report_path = Path(html_report_path)
        if not self.is_configured:
            return {"status": "disabled", "public_report_url": ""}

        command = self._resolve_command()
        if not command:
            return {"status": "unavailable", "public_report_url": ""}

        project_dir = self._resolve_project_dir(html_report_path)
        cmd = [
            *command,
            "--cwd",
            str(project_dir),
            "--token",
            self.config.token,
            "--yes",
        ]
        if self.config.scope:
            cmd.extend(["--scope", self.config.scope])

        try:
            completed = self.runner(
                cmd,
                cwd=str(self.base_dir),
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except Exception as exc:
            return {
                "status": "failed",
                "public_report_url": "",
                "error": str(exc),
            }

        deployment_url = self._extract_deployment_url(completed.stdout)
        if not deployment_url:
            return {
                "status": "failed",
                "public_report_url": "",
                "error": completed.stdout or completed.stderr,
            }

        return {
            "status": "published",
            "deployment_url": deployment_url,
            "public_report_url": f"{deployment_url.rstrip('/')}/{html_report_path.name}",
        }

    def _resolve_project_dir(self, html_report_path: Path) -> Path:
        configured = (self.base_dir / self.config.project_dir).resolve()
        if html_report_path.parent.resolve() == configured:
            return configured
        return html_report_path.parent.resolve()

    def _resolve_command(self) -> Optional[list[str]]:
        vercel = shutil.which("vercel")
        if vercel:
            return [vercel]

        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if npx:
            return [npx, "vercel"]
        return None

    def _extract_deployment_url(self, stdout: str) -> str:
        for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
            if line.startswith("https://") or line.startswith("http://"):
                return line
        return ""
