from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_clients import AIClientConfig, OpenAICompatibleClient
from html_report_renderer import HTMLReportRenderer
from langgraph_flows import (
    build_dingtalk_task_graph as _build_dingtalk_task_graph_impl,
    build_dingtalk_workflow_graph as _build_dingtalk_workflow_graph_impl,
)
from qualitative_research import (
    IncompleteResearchRunError,
    QualitativeResearchInput,
    QualitativeResearchRunner,
)
from report_publisher import VercelStaticPublisher
from task_session_manager import TaskSessionManager


def build_dingtalk_workflow_graph(workflow):
    return _build_dingtalk_workflow_graph_impl(workflow)


def build_dingtalk_task_graph(workflow):
    return _build_dingtalk_task_graph_impl(workflow)


class DingTalkBotWorkflow:
    def __init__(
        self,
        persona_path: Path | str,
        session_dir: Path | str,
        output_dir: Path | str,
        ai_client=None,
        report_publisher=None,
    ):
        self.persona_path = Path(persona_path)
        if ai_client is None:
            default_config = AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent)
            default_config.timeout_seconds = max(default_config.timeout_seconds, 180.0)
            self.ai_client = OpenAICompatibleClient(config=default_config)
        else:
            self.ai_client = ai_client
        self.session_manager = TaskSessionManager(session_dir, persona_path=self.persona_path, ai_client=self.ai_client)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.research_input_cls = QualitativeResearchInput
        self.runner = QualitativeResearchRunner(self.persona_path, ai_client=self.ai_client)
        self.renderer = HTMLReportRenderer()
        self.report_publisher = report_publisher or VercelStaticPublisher(base_dir=Path(__file__).resolve().parent)
        self.graph = build_dingtalk_workflow_graph(self)
        self.task_graph = build_dingtalk_task_graph(self)

    def handle_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            state = self.graph.invoke({"event": event})
            return state["response"]
        except Exception:
            session = self.session_manager.get_or_create(
                group_id=event["group_id"],
                conversation_id=event["conversation_id"],
                user_id=event["user_id"],
            )
            session.status = "error"
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "处理研究任务时发生错误，请稍后再试。"}],
            )

    def run_pending_task(self, task_id: str) -> Dict[str, Any]:
        try:
            state = self.task_graph.invoke({"task_id": task_id})
            return state["response"]
        except IncompleteResearchRunError:
            session = self._load_session_by_task_id(task_id)
            session.status = "error"
            session.html_report_path = None
            session.json_report_path = None
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "本次结果不完整，请稍后重试"}],
                html_report_path=None,
                json_report_path=None,
            )
        except Exception:
            session = self._load_session_by_task_id(task_id)
            session.status = "error"
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "生成研究报告时发生错误，请稍后再试。"}],
            )

    def _build_short_summary(self, report: Dict[str, Any]) -> str:
        summary = report.get("research_summary", {})
        mode = report.get("meta", {}).get("mode", "multi")
        mode_label = "多人模式" if mode == "multi" else "单人模式"
        consensus = (summary.get("consensus") or ["多数妈妈会先看信息是否可信。"])[0]
        barrier = (summary.get("barriers") or ["主要障碍是信息还不够清楚。"])[0]
        covered = (
            f"{report.get('meta', {}).get('total_agents', 0)} 位妈妈画像"
            if mode == "multi"
            else report.get("appendix", {}).get("selected_persona") or "指定妈妈画像"
        )
        return f"{mode_label}，覆盖 {covered}。{consensus} {barrier}"

    def _load_session_by_task_id(self, task_id: str):
        session_id = task_id.rsplit("__run", 1)[0]
        return self.session_manager.load(session_id)

    def _response(
        self,
        session,
        messages: List[Dict[str, Any]],
        task_id: Optional[str] = None,
        html_report_path: Optional[str] = None,
        json_report_path: Optional[str] = None,
        public_report_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "status": session.status,
            "session_id": session.session_id,
            "task_id": task_id or session.last_task_id,
            "messages": messages,
            "html_report_path": html_report_path or session.html_report_path,
            "json_report_path": json_report_path or session.json_report_path,
            "public_report_url": public_report_url,
        }
