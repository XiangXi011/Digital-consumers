from pathlib import Path

from dingtalk_bot import DingTalkBotWorkflow
from dingtalk_stream_service import DingTalkStreamBotService


def main():
    base_dir = Path(__file__).resolve().parent
    workflow = DingTalkBotWorkflow(
        persona_path=base_dir / "persona_samples_complete.json",
        session_dir=base_dir / "outputs" / "dingtalk_sessions",
        output_dir=base_dir / "outputs" / "dingtalk_reports",
    )
    service = DingTalkStreamBotService(workflow)
    service.start_forever()


if __name__ == "__main__":
    main()
