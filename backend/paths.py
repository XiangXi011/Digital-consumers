from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
OUTPUTS_DIR = REPO_ROOT / "outputs"
PERSONAS_DIR = REPO_ROOT / "personas"
DOTENV_PATH = REPO_ROOT / ".env"
PERSONA_SAMPLES_PATH = REPO_ROOT / "persona_samples.json"
PERSONA_COMPLETE_PATH = REPO_ROOT / "persona_samples_complete.json"
DINGTALK_SESSIONS_DIR = OUTPUTS_DIR / "dingtalk_sessions"
DEBUG_SESSIONS_DIR = OUTPUTS_DIR / "debug_sessions"
DINGTALK_REPORTS_DIR = OUTPUTS_DIR / "dingtalk_reports"
WEB_UPLOADS_DIR = OUTPUTS_DIR / "web_uploads"
REPORT_SHARES_PATH = OUTPUTS_DIR / "report_shares.json"
