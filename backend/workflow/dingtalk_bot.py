from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.infra.ai_clients import AIClientConfig, OpenAICompatibleClient
from backend.paths import REPO_ROOT
from backend.research.html_report_renderer import HTMLReportRenderer
from backend.research.qualitative_research import (
    IncompleteResearchRunError,
    QualitativeResearchInput,
    QualitativeResearchRunner,
    ResearchPlannerBlockedError,
)
from backend.research.report_publisher import VercelStaticPublisher
from backend.workflow.langgraph_flows import (
    build_dingtalk_task_graph as _build_dingtalk_task_graph_impl,
    build_dingtalk_workflow_graph as _build_dingtalk_workflow_graph_impl,
)
from backend.workflow.task_session_manager import TaskSessionManager


logger = logging.getLogger(__name__)

DEFAULT_TASK_TIMEOUT_SECONDS = 600.0


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
            config=AIClientConfig.from_env(base_dir=REPO_ROOT)
        )
        self.session_manager = TaskSessionManager(
            session_dir,
            persona_path=self.persona_path,
            ai_client=self.ai_client,
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.research_input_cls = QualitativeResearchInput
        self.runner = QualitativeResearchRunner(self.persona_path, ai_client=self.ai_client)
        self.renderer = HTMLReportRenderer()
        self.report_publisher = report_publisher or VercelStaticPublisher(
            base_dir=REPO_ROOT
        )
        self.task_timeout_seconds = self._load_task_timeout()
        self.graph = build_dingtalk_workflow_graph(self)
        self.task_graph = build_dingtalk_task_graph(self)

    def _load_task_timeout(self) -> float:
        """Load task timeout from environment variable with fallback to default."""
        timeout_str = os.environ.get("DINGTALK_TASK_TIMEOUT_SECONDS", "")
        if timeout_str:
            try:
                timeout = float(timeout_str)
                if timeout > 0:
                    return timeout
                logger.warning("DINGTALK_TASK_TIMEOUT_SECONDS must be positive, using default")
            except ValueError:
                logger.warning("Invalid DINGTALK_TASK_TIMEOUT_SECONDS value '%s', using default", timeout_str)
        return DEFAULT_TASK_TIMEOUT_SECONDS

    def handle_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        try:
            state = self.graph.invoke({"event": event})
            return state["response"]
        except Exception:
            logger.exception(
                "Workflow handle_message failed for group_id=%s conversation_id=%s user_id=%s",
                event.get("group_id"),
                event.get("conversation_id"),
                event.get("user_id"),
            )
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
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self.task_graph.invoke, {"task_id": task_id})
            state = future.result(timeout=self.task_timeout_seconds)
            return state["response"]
        except FuturesTimeoutError:
            logger.warning("Task %s timed out after %.1f seconds", task_id, self.task_timeout_seconds)
            future.cancel()
            # Attempt to shutdown executor without waiting for running tasks
            executor.shutdown(wait=False, cancel_futures=True)
            session = self._load_session_by_task_id(task_id)
            session.status = "recovery"
            session.html_report_path = None
            session.json_report_path = None
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "本次任务执行超时，请稍后重试或补充更聚焦的信息。"}],
            )
        except ResearchPlannerBlockedError as exc:
            executor.shutdown(wait=False)
            session = self._load_session_by_task_id(task_id)
            session.status = "awaiting_clarification"
            session.research_plan = exc.research_plan
            session.last_task_id = None
            session.html_report_path = None
            session.json_report_path = None
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": self.session_manager.build_clarification_text(session)}],
                task_id=None,
            )
        except IncompleteResearchRunError as exc:
            executor.shutdown(wait=False)
            logger.exception(
                "Task %s failed because research output was incomplete: %s",
                task_id,
                exc,
            )
            session = self._load_session_by_task_id(task_id)
            session.status = "error"
            session.html_report_path = None
            session.json_report_path = None
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "本次结果不完整，请稍后重试"}],
            )
        except Exception:
            executor.shutdown(wait=False)
            logger.exception("Task %s failed unexpectedly during report generation.", task_id)
            session = self._load_session_by_task_id(task_id)
            session.status = "error"
            self.session_manager.save(session)
            return self._response(
                session,
                [{"type": "text", "content": "生成研究报告时发生错误，请稍后再试。"}],
            )

    def _build_short_summary(self, report: Dict[str, Any]) -> str:
        summary = report.get("research_summary", {})
        structured = report.get("structured_recommendation", {})
        meta = report.get("meta", {})
        mode = meta.get("mode", "multi")
        mode_label = "多人模式" if mode == "multi" else "单人模式"
        covered = (
            f"{meta.get('total_agents', 0)} 位妈妈画像"
            if mode == "multi"
            else report.get("appendix", {}).get("selected_persona") or "指定妈妈画像"
        )

        decision = "建议推进"
        key_risks = structured.get("key_risks") or summary.get("barriers") or []
        opportunity = structured.get("opportunity_areas") or summary.get("drivers") or []
        if key_risks and not opportunity:
            decision = "建议先优化后推进"

        objective = (
            structured.get("objective_answers")
            or summary.get("consensus")
            or ["当前有一定消费者兴趣，但需要结合场景细化。"]
        )[0]
        evidence_list = (summary.get("drivers") or [])[:2]
        risk_line = (key_risks or ["主要风险是信息可信度与卖点清晰度不足。"])[0]
        next_action = (
            (structured.get("recommended_actions") or ["补充关键信息后复跑，验证关键阻力是否下降。"])[0]
            if isinstance(structured.get("recommended_actions"), list)
            else "补充关键信息后复跑，验证关键阻力是否下降。"
        )

        evidence_text = "；".join(str(item).strip() for item in evidence_list if str(item).strip())
        if not evidence_text:
            evidence_text = "已有共识点支持继续验证。"

        required_for_quality = [
            meta.get("question_type", ""),
            report.get("research_brief", {}).get("user_question", ""),
            report.get("research_brief", {}).get("product_info", ""),
        ]
        present_count = sum(1 for item in required_for_quality if str(item).strip())
        if present_count >= 3:
            completeness = "高"
        elif present_count == 2:
            completeness = "中"
        else:
            completeness = "低"

        return (
            f"【决策卡】\n"
            f"- 结论：{decision}\n"
            f"- 信息完整度：{completeness}\n"
            f"- 覆盖范围：{mode_label}，{covered}\n"
            f"- 核心判断：{objective}\n"
            f"- 关键证据：{evidence_text}\n"
            f"- 主要风险：{risk_line}\n"
            f"- 下一步动作：{next_action}"
        )

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
