from dataclasses import dataclass, field
from typing import List, Optional
from openenv.core.env_server import Action, Observation, State


@dataclass
class EmailTriageAction(Action):
    priority: str   # "urgent", "normal", "low"
    category: str   # "billing", "technical", "general", "spam"
    response: str   # draft response text


@dataclass
class EmailTriageObservation(Observation):
    done: bool
    reward: Optional[float]
    email_subject: str
    email_body: str
    email_sender: str
    task_name: str
    message: str


@dataclass
class EmailTriageState(State):
    episode_id: Optional[str] = None
    step_count: int = 0
    task_name: str = ""