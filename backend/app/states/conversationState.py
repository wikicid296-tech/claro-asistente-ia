import time
from dataclasses import dataclass,field
from typing import Dict,Optional
@dataclass
class ConversationState:
    intent: Optional[str] = None
    slots: Dict[str, str] = field(default_factory=dict)
    awaiting_slot: Optional[str] = None
    original_query: Optional[str] = None   # 👈 NUEVO
    updated_at: float = field(default_factory=time.time)
