"""Deterministic stub runners (no LLM required)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.runners.base import RoleRunner, RunContext, RunResult


class StubCeoRunner(RoleRunner):
    role_id = "ceo"

    async def run(self, ctx: RunContext) -> RunResult:
        return RunResult(
            artifact_id=f"art-memo-{uuid4().hex[:6]}",
            artifact_title="CEO 评估备忘",
            artifact_type="memo",
            artifact_content=(
                f"# 立项评估\n\n"
                f"项目 `{ctx.project_id}` · 任务：{ctx.task.get('title')}\n\n"
                f"**结论：** 可继续推进，建议 Founder 关注预算与验收边界。\n"
            ),
            progress_note="CEO 评估完成",
            tokens_in=800,
            tokens_out=400,
        )


class StubProductRunner(RoleRunner):
    role_id = "product"

    async def run(self, ctx: RunContext) -> RunResult:
        return RunResult(
            artifact_id=f"art-prd-{uuid4().hex[:6]}",
            artifact_title="PRD 草稿",
            artifact_type="prd",
            artifact_content=(
                f"# PRD · {ctx.project_id}\n\n"
                f"## 目标\n自动化核心流程。\n\n## 验收\nHITL 卡点 4 处。\n"
            ),
            handoff_to="ceo",
            progress_note="PRD 初稿完成",
            tokens_in=1200,
            tokens_out=900,
        )


class StubLegalRunner(RoleRunner):
    role_id = "legal"

    async def run(self, ctx: RunContext) -> RunResult:
        from app.deliverables.kinds import resolve_deliverable
        from app.deliverables.templates import get_template

        title = ctx.task.get("title", "")
        spec = resolve_deliverable(
            "legal",
            title,
            directive_kind=ctx.task.get("deliverableKind"),
            brief_context=ctx.task.get("briefContext") or "",
        )
        tpl = get_template(spec.template_id)
        project = next(
            (p for p in ctx.dashboard.get("projects", []) if p.get("id") == ctx.project_id),
            {},
        )
        client = (project.get("clientName") or ctx.project_id).replace("（线索）", "")
        content = tpl.skeleton.replace("[待填写：合作事项/项目名称]", client)
        return RunResult(
            artifact_id=f"art-{spec.kind}-{uuid4().hex[:6]}",
            artifact_title=spec.title,
            artifact_type=spec.kind,
            artifact_kind=spec.kind,
            artifact_format=spec.format,
            artifact_viewer=spec.viewer,
            artifact_group=spec.group,
            template_id=spec.template_id,
            artifact_content=content,
            handoff_to="ceo",
            progress_note=f"法务 {spec.title} 完成（Stub · 配置 API Key 后可 LLM 定稿）",
            tokens_in=600,
            tokens_out=400,
        )


class StubDevRunner(RoleRunner):
    role_id = "dev"

    async def run(self, ctx: RunContext) -> RunResult:
        from app.deliverables.kinds import resolve_deliverable

        title = ctx.task.get("title", "")
        spec = resolve_deliverable(
            "dev",
            title,
            directive_kind=ctx.task.get("deliverableKind"),
        )
        if spec.kind == "demo" or ctx.task.get("deliverableKind") == "demo":
            return RunResult(
                artifact_id=f"art-demo-{uuid4().hex[:6]}",
                artifact_title="Demo 交付说明",
                artifact_type="demo",
                artifact_kind="demo",
                artifact_format="link",
                artifact_viewer="demo",
                artifact_group="engineering",
                template_id="dev.demo",
                artifact_content=(
                    f"# Demo · {ctx.project_id}\n\n"
                    "**URL:** `https://staging.example.com/poc`\n\n"
                    "## 自测\n- [x] 主流程\n- [ ] 边界用例\n"
                ),
                demo_url="https://staging.example.com/poc",
                handoff_to="ceo",
                progress_note="Demo 说明完成",
                tokens_in=800,
                tokens_out=400,
            )
        files = [
            {
                "path": "src/main.py",
                "language": "python",
                "content": (
                    '"""PoC entrypoint."""\n\n'
                    "def run_pipeline(sample_path: str) -> dict:\n"
                    '    return {"status": "ok", "sample": sample_path}\n\n'
                    'if __name__ == "__main__":\n'
                    '    print(run_pipeline("samples/demo.json"))\n'
                ),
            },
            {
                "path": "README.md",
                "language": "markdown",
                "content": (
                    f"# {ctx.project_id} · PoC\n\n"
                    "## 运行\n```bash\npython src/main.py\n```\n"
                ),
            },
            {
                "path": "requirements.txt",
                "language": "text",
                "content": "requests>=2.31\n",
            },
        ]
        content = (
            f"# 代码交付 · {ctx.project_id}\n\n"
            "## 目录\n- `src/main.py` — PoC 入口\n- `requirements.txt`\n\n"
            "## 自测\n- [x] 本地运行\n- [ ] 集成测试\n"
        )
        return RunResult(
            artifact_id=f"art-{spec.kind}-{uuid4().hex[:6]}",
            artifact_title=spec.title,
            artifact_type=spec.kind,
            artifact_kind=spec.kind,
            artifact_format="code",
            artifact_viewer="code",
            artifact_group=spec.group,
            template_id=spec.template_id,
            artifact_content=content,
            artifact_files=files,
            handoff_to="ceo",
            progress_note="开发代码包完成",
            tokens_in=2000,
            tokens_out=1500,
        )


class StubOpsRunner(RoleRunner):
    role_id = "ops"

    async def run(self, ctx: RunContext) -> RunResult:
        title = ctx.task.get("title", "")
        if "台账" in title:
            return RunResult(
                artifact_id=f"art-ops-{uuid4().hex[:6]}",
                artifact_title="线索台账更新",
                artifact_type="doc",
                artifact_content=(
                    f"# 线索台账 · {ctx.project_id}\n\n"
                    "| 客户 | 阶段 | 下一步 | 负责人 |\n"
                    "|------|------|--------|--------|\n"
                    f"| {ctx.project_id} | 线索 | 待 NDA | 运营 |\n"
                ),
                handoff_to="ceo",
                progress_note="线索台账已更新",
                tokens_in=300,
                tokens_out=150,
            )
        return RunResult(
            artifact_id=f"art-ops-{uuid4().hex[:6]}",
            artifact_title="结项清单",
            artifact_type="doc",
            artifact_content="# 结项清单\n\n- [ ] 客户 ZIP\n- [ ] 验收确认\n",
            handoff_to="ceo",
            progress_note="结项清单已起草",
            tokens_in=400,
            tokens_out=200,
        )


RUNNERS: dict[str, RoleRunner] = {
    "ceo": StubCeoRunner(),
    "product": StubProductRunner(),
    "legal": StubLegalRunner(),
    "dev": StubDevRunner(),
    "ops": StubOpsRunner(),
}


def get_runner(role_id: str) -> RoleRunner | None:
    return RUNNERS.get(role_id)
