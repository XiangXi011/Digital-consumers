# DingTalk User-Scoped Session Reset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为钉钉群机器人增加“新任务/重置任务”指令，并将任务会话改为按发起人隔离，保证重置只影响当前发起人的任务。

**Architecture:** 保留现有 LangGraph 主图和分析子图，只重构会话标识与主图前置分支。`TaskSessionManager` 负责按 `group_id + conversation_id + user_id` 存取与重置会话，LangGraph 主图新增命令检测与重置节点，Stream 入口按当前发起人判断是否续接会话。

**Tech Stack:** Python, LangGraph, unittest, DingTalk Stream SDK

---

### Task 1: Add failing session-isolation tests

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_workflow.py`

**Step 1: Write the failing test**

Add tests covering:

```python
def test_same_group_different_users_have_independent_sessions():
    ...

def test_reset_command_clears_only_current_users_session():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_same_group_different_users_have_independent_sessions tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_reset_command_clears_only_current_users_session -v
```

Expected: FAIL because current session key is still group-scoped and reset behavior does not exist.

**Step 3: Write minimal implementation**

Do not implement here. Move to Task 2 and Task 3.

**Step 4: Run test to verify it passes**

Re-run the same command after Tasks 2 and 3.

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 2: Refactor TaskSessionManager to user-scoped sessions

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/task_session_manager.py`

**Step 1: Write the failing test**

Covered by Task 1.

**Step 2: Run test to verify it fails**

Covered by Task 1.

**Step 3: Write minimal implementation**

Implement:

- `_build_session_id(group_id, conversation_id, user_id)`
- `has_session_for(group_id, conversation_id, user_id)`
- `find_session_for(group_id, conversation_id, user_id)`
- `get_or_create(group_id, conversation_id, user_id)`
- `reset_session(group_id, conversation_id, user_id)`

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_same_group_different_users_have_independent_sessions -v
```

Expected: PASS

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 3: Add reset command handling to the LangGraph workflow

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_nodes.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_flows.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/langgraph_state.py`

**Step 1: Write the failing test**

Covered by Task 1.

**Step 2: Run test to verify it fails**

Covered by Task 1.

**Step 3: Write minimal implementation**

Implement:

- reset command tokens
- `detect_command` node
- `reset_session` node
- route from `load_session -> detect_command -> reset_session/send_checklist/ingest_message`
- state fields needed for command detection

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_dingtalk_workflow.DingTalkWorkflowTest.test_reset_command_clears_only_current_users_session -v
```

Expected: PASS

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 4: Fix Stream handler session continuation rules

**Files:**
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/tests/test_dingtalk_stream_service.py`
- Modify: `C:/Users/05537/Desktop/agent/市场部agent teams/dingtalk_stream_service.py`

**Step 1: Write the failing test**

Add tests covering:

```python
def test_group_message_without_at_only_continues_current_users_session():
    ...

def test_reset_command_without_existing_session_starts_fresh_checklist():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_dingtalk_stream_service.DingTalkStreamServiceTest.test_group_message_without_at_only_continues_current_users_session -v
```

Expected: FAIL because `_should_process()` still looks up group-scoped sessions.

**Step 3: Write minimal implementation**

Update `_should_process()` to find session by `group_id + conversation_id + current user_id`.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.test_dingtalk_stream_service.DingTalkStreamServiceTest.test_group_message_without_at_only_continues_current_users_session -v
```

Expected: PASS

**Step 5: Commit**

Repository is not a git repo. Skip commit.

### Task 5: Run focused and full verification

**Files:**
- No code changes required

**Step 1: Run focused workflow tests**

```powershell
python -m unittest tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 2: Run broader regression tests**

```powershell
python -m unittest tests.test_concept_testing tests.test_generate_personas_constraints tests.test_advanced_testing tests.test_dingtalk_workflow tests.test_dingtalk_stream_service -v
```

Expected: PASS

**Step 3: Smoke-check the bot entry point**

```powershell
python .\run_dingtalk_demo.py
```

Expected: demo flow still completes and emits checklist / follow-up / report output.

**Step 4: Commit**

Repository is not a git repo. Skip commit.
