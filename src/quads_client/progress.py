from typing import Any, Optional


# Keep in sync with MoveStatus enum / Schedule.PROGRESSIVE_STAGES in quads/server/models.py
MOVE_STAGES = [
    "pending",
    "switch_config",
    "ipmi_config",
    "hardware_prep",
    "power_on",
    "provisioning",
    "cleanup",
    "reboot",
    "post_install",
    "foreman_rbac",
    "validation",
    "released",
]
TOTAL_STAGES = len(MOVE_STAGES)


def stage_of(status):
    if status in ("completed", "failed"):
        return TOTAL_STAGES
    try:
        return MOVE_STAGES.index(status) + 1
    except ValueError:
        return 0


def format_progress_str(status):
    stage = stage_of(status)
    if status == "failed":
        return "FAILED"
    if status == "completed":
        return f"{TOTAL_STAGES}/{TOTAL_STAGES}"
    return f"{stage}/{TOTAL_STAGES}"


class ProgressTracker:
    def __init__(self, api):
        self._api = api

    def get_move_status(self, host: str) -> Optional[dict[str, Any]]:
        try:
            return self._api.get_move_status(host)
        except Exception:
            return None

    def get_all_active_moves(self) -> list:
        try:
            return self._api.get_all_move_status()
        except Exception:
            return []

    def format_stage_progress(self, host: str) -> str:
        data = self.get_move_status(host)
        if not data:
            return ""
        status = data.get("status", "pending")
        return format_progress_str(status)
