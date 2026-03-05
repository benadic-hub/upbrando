from __future__ import annotations

from app.db.models import AgentProfile, User


def check_agent_run_permission(
    *,
    user: User,
    agent_profile: AgentProfile | None,
    tool_name: str,
    department_id: str | None,
) -> tuple[bool, str]:
    if user.role.value != "AI_AGENT":
        return True, "User is not an AI agent"
    if not agent_profile:
        return False, "Agent profile not found"
    if tool_name not in set(agent_profile.tools_allowed or []):
        return False, f"Tool '{tool_name}' is not in tools_allowed"
    if department_id and str(user.department_id) != department_id:
        return False, "Department mismatch"
    return True, "Allowed"

