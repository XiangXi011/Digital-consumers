# DingTalk User-Scoped Session Reset Design

**Date:** 2026-03-10

## Goal

为钉钉群机器人增加 `新任务 / 重置任务 / 清空任务 / 重新开始` 指令，并把任务会话从“群级共享”改为“当前群 + 当前会话 + 当前发起人”隔离，确保重置只影响当前发起人的任务。

## Current Problem

- 当前会话主键是 `group_id + conversation_id`，同群内不同发起人会共享一个任务上下文。
- 用户在群里补充资料时，即使意图是自己的任务，也可能续接到别人的上下文。
- `新任务/重置任务` 如果只做当前实现层面的删除，实际删除的是整群当前任务，不符合“只清空当前发起人的任务会话”的要求。

## Recommended Approach

采用“按发起人隔离的会话模型 + LangGraph 显式重置分支”。

### Session Identity

- 会话主键从 `group_id + conversation_id` 改为 `group_id + conversation_id + user_id`
- `TaskSessionManager` 的查询、创建、加载、存在性判断全部改为按这三个维度进行
- 历史旧会话文件不再复用，新版本仅识别新主键

### Reset Commands

以下文本视为同义重置命令：

- `新任务`
- `重置任务`
- `清空任务`
- `重新开始`

行为定义：

- 当前发起人在当前群发出任一命令后，只删除自己的当前任务会话
- 删除后立即创建一个新的空会话
- 机器人回复“已为你清空当前群里的当前任务”并紧接完整资料清单
- 不删除历史 HTML/JSON 报告文件

### Workflow Routing

主图增加显式命令检测与重置分支：

1. `load_session`
2. `detect_command`
3. 如果命中重置命令：
   - `reset_session`
   - `send_checklist`
4. 否则：
   - `ingest_message`
   - `send_follow_up / send_minimum_required / start_analysis`

这样可避免把“新任务”误判为普通文本字段。

### DingTalk Stream Behavior

- 群消息未 `@` 机器人时，只有当“当前发起人”在当前群/会话内存在自己的活跃 session，才继续处理
- 同群其他人的活跃 session 不会让当前用户的消息被误接管

## Data and Compatibility

- 老的群级 session 文件保留在磁盘上，但不会继续读写
- 新版只会创建按用户隔离的新 session 文件
- 不做自动迁移，避免把旧的共享状态继续带入新模型

## Error Handling

- 如果用户发送重置命令但此前没有 session，也仍然创建一个新空会话并返回资料清单
- 如果重置时删除文件失败，保留原会话并返回错误节点

## Testing Strategy

### Session Layer

- 同群同会话下，不同 `user_id` 创建不同 session
- 重置只删除当前用户自己的 session

### Workflow Layer

- 已有资料时发送 `新任务`，返回重置提示和完整资料清单
- 重置后再次补资料，不继承上一轮字段或 `last_task_id`

### Stream Layer

- 用户 A 的活跃 session 不应让用户 B 在同群的普通消息被处理
- 用户自己即使不再 `@` 机器人，后续补图/补资料仍能续接到自己的任务

## Files Expected To Change

- `task_session_manager.py`
- `langgraph_nodes.py`
- `langgraph_flows.py`
- `dingtalk_stream_service.py`
- `langgraph_state.py`
- `tests/test_dingtalk_workflow.py`
- `tests/test_dingtalk_stream_service.py`

## Non-Goals

- 不支持“同一个用户在同一群同时维护多个未完成任务”
- 不做历史 session 自动迁移
- 不改分析链路、报告生成链路和 Vercel 发布链路
