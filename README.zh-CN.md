# Nora（中文入口）

Nora 是一个个人研究工作流系统：维护研究项目上下文、唤醒长期搁置的项目、在多次 agent 会话之间持续追踪进展，并提供引用审计、文献管理、写作辅助三个可选模块。

> 本文档是入口简介，完整文档见英文 [README.md](README.md)——功能细节、skill 用法、状态文件说明均以英文版为准。

## 核心理念

- 全局 skill 教 agent 怎么干活，项目本地状态放在 `.nora/`。
- 结构化状态是唯一真相，agent 会话开始时读状态、结束时**提议**（而非静默应用）更新。
- 改变研究状态的建议要过决策门（`.nora/decisions/decisions.yaml`）：agent 只能提 `pending` 提案，批准权在你。
- `.nora/` 默认不进 git（`nora new` 自动生成 `.nora/.gitignore`），要分享就显式导出。
- 工作区解析像 git 找 `.git` 一样：就近祖先原则（`nora root`）。同一研究课题的多个并列工作区是常态，不是冲突。

## 快速开始

需要 Python 3.8+（纯标准库，无需安装任何包）。

```bash
nora install-skills   # 把四个 skill 符号链接进 Claude Code / Codex
nora new              # 在当前目录搭建核心 .nora/ 状态 + AGENTS.md
nora doctor           # 检查全局安装 + 项目状态 + 可选模块

# 按需启用可选模块（都不是必需的）:
nora citation init    # 引用/BibTeX 审计
nora literature init  # 文献追踪(papers.yaml 结构化状态 + 决策门强制)
nora writing init     # 写作辅助(nora writing lint 机械护栏)
```

在 agent 会话里使用（以 Claude Code 为例）：

```text
/nora                 # 加载项目上下文,正常对话
/nora reboot          # 唤醒搁置项目
/nora session-update  # 会话收尾,提议状态更新
/nora-citation check-bibtex
/nora-literature triage
/nora-writing polish
```

## 状态一览

```text
.nora/
  .gitignore          # '*',状态默认不进 git
  config.yaml         # 工作区身份(project_id / workspace_id / workspace_type)
  PROJECT_STATE.yaml  # 项目状态
  CONTEXT_BRIEF.md    # 项目简报
  SESSION_LOG.md      # 会话日志
  NEXT_ACTIONS.md     # 下一步行动
  OPEN_LOOPS.md       # 未决事项
  decisions/          # 决策门
```

**状态：alpha。** 功能均可用，但尚未经过大量真实项目验证。
