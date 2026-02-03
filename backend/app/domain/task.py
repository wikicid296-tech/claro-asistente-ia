from dataclasses import dataclass, field
from typing import Optional, Literal
import time
import uuid

TaskType = Literal["reminder", "calendar", "note"]
TaskStatus = Literal["created", "active", "completed"]
MeetingType = Literal["virtual", "presencial"]
@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_key: str = ""
    type: TaskType = "note"
    content: str = ""
    description: Optional[str] = None
    meeting_type: Optional[MeetingType] = None
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    status: TaskStatus = "active"
    created_at: float = field(default_factory=time.time)

