from pathlib import Path
from typing import Any, Dict, List, Optional

from advanced_testing import AdvancedTestRunner
from ai_clients import AIClientConfig, OpenAICompatibleClient
from concept_testing import ConceptTestInput, ConceptTestRunner
from html_report_renderer import HTMLReportRenderer
from langgraph_flows import (
    build_dingtalk_task_graph as _build_dingtalk_task_graph_impl,
    build_dingtalk_workflow_graph as _build_dingtalk_workflow_graph_impl,
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
        self.ai_client = ai_client or OpenAICompatibleClient(
            config=AIClientConfig.from_env(base_dir=Path(__file__).resolve().parent)
        )
        self.session_manager = TaskSessionManager(session_dir, ai_client=self.ai_client)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.concept_input_cls = ConceptTestInput
        self.runner = ConceptTestRunner(self.persona_path, ai_client=self.ai_client)
        self.advanced_runner = AdvancedTestRunner(self.persona_path, ai_client=self.ai_client)
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
                [{"type": "text", "content": "绯荤粺鍦ㄥ鐞嗕换鍔℃椂鍑虹幇寮傚父锛岃绋嶅悗閲嶈瘯銆?"}],
            )

    def run_pending_task(self, task_id: str) -> Dict[str, Any]:
        try:
            state = self.task_graph.invoke({"task_id": task_id})
            return state["response"]
        except Exception:
            session = self._load_session_by_task_id(task_id)
            session.status = "error"
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "绯荤粺鍦ㄧ敓鎴愭姤鍛婃椂鍑虹幇寮傚父锛岃绋嶅悗閲嶈瘯銆?"}],
            )

    def _build_short_summary(self, report: Dict[str, Any]) -> str:
        top_segment = (
            report["segment_opportunity"]["top_segments"][0]["segment"]
            if report["segment_opportunity"]["top_segments"]
            else "未识别"
        )
        recommendation_label = self._translate_recommendation(
            report["executive_summary"]["recommendation"]
        )
        return (
            f"{report['executive_summary']['headline']} "
            f"当前建议：{recommendation_label}。"
            f"高潜人群：{top_segment}。"
            f"预计转化率：{report['purchase_intent']['estimated_conversion_rate']}%。"
        )

    def _translate_recommendation(self, recommendation: str) -> str:
        mapping = {
            "advance_to_real_research": "可进入真实调研验证",
            "revise_then_retest": "建议优化后再测",
            "do_not_advance_yet": "暂不建议推进",
        }
        return mapping.get(recommendation, recommendation)

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
