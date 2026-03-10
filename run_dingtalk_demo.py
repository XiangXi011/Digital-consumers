from pathlib import Path
from uuid import uuid4

from dingtalk_bot import DingTalkBotWorkflow


def print_messages(title: str, result: dict):
    print(f"\n[{title}] status={result['status']}")
    for message in result["messages"]:
        print(message["content"])
    if result.get("task_id"):
        print(f"task_id={result['task_id']}")
    if result.get("html_report_path"):
        print(f"html_report_path={result['html_report_path']}")
    if result.get("json_report_path"):
        print(f"json_report_path={result['json_report_path']}")


def main():
    base_dir = Path(__file__).resolve().parent
    session_dir = base_dir / "outputs" / "dingtalk_sessions"
    output_dir = base_dir / "outputs" / "dingtalk_reports"
    group_id = "demo-group"
    conversation_id = f"demo-conversation-{uuid4().hex[:8]}"
    user_id = "demo-user"

    bot = DingTalkBotWorkflow(
        persona_path=base_dir / "persona_samples_complete.json",
        session_dir=session_dir,
        output_dir=output_dir,
    )

    start = bot.handle_message(
        {
            "group_id": group_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "text": "@机器人 我要做新品测试",
        }
    )
    print_messages("首次响应", start)

    provide = bot.handle_message(
        {
            "group_id": group_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "text": (
                "产品/方案名称：舒客儿童益生菌防蛀牙膏概念版\n"
                "品牌：舒客\n"
                "品类：儿童口腔护理\n"
                "核心卖点：益生菌配方；低氟防蛀；孩子更愿意坚持刷牙\n"
                "价格：39.9元\n"
                "包装信息：卡通水果视觉，突出年龄段和防蛀卖点。\n"
                "目标渠道：天猫；京东；母婴店\n"
            ),
        }
    )
    print_messages("补充资料", provide)

    confirm = bot.handle_message(
        {
            "group_id": group_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "text": "按现有资料运行",
        }
    )
    print_messages("开始分析", confirm)

    completed = bot.run_pending_task(confirm["task_id"])
    print_messages("分析完成", completed)


if __name__ == "__main__":
    main()
