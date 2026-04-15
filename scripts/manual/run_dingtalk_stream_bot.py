import logging
from pathlib import Path

from dingtalk_bot import DingTalkBotWorkflow
from dingtalk_stream_service import DingTalkStreamBotService

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到stderr
    ]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting DingTalk Stream Bot...")
    base_dir = Path(__file__).resolve().parent
    workflow = DingTalkBotWorkflow(
        persona_path=base_dir / "persona_samples_complete.json",
        session_dir=base_dir / "outputs" / "dingtalk_sessions",
        output_dir=base_dir / "outputs" / "dingtalk_reports",
    )
    logger.info("Workflow initialized")
    service = DingTalkStreamBotService(workflow)
    logger.info("Service created, starting forever loop...")
    service.start_forever()


if __name__ == "__main__":
    main()
