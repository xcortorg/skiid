from logging import getLogger
from typing import Dict, List, Optional

log = getLogger("evict/processors")

def process_audit_threshold(
    action_history: List[Dict], 
    threshold: int,
    timeframe: int
) -> bool:
    """
    Process audit log threshold checks in a separate process.
    """
    recent_actions = len(action_history)
    return recent_actions >= threshold

def process_whitelist_check(
    user_id: int,
    whitelist_ids: List[int]
) -> bool:
    """
    Process whitelist checks in a separate process.
    """
    return user_id in whitelist_ids

def process_punishment_data(
    guild_data: Dict,
    module: str,
    action_type: str,
    details: Optional[str] = None
) -> Dict:
    """
    Process punishment data formatting in a separate process.
    """
    punishment_data = {
        'reason': f"{module.title()} {action_type} attempt detected",
        'audit_reason': f"[Antinuke] {module.title()} {action_type} attempt"
    }
    
    if details:
        punishment_data['reason'] += f" | {details}"

    return punishment_data