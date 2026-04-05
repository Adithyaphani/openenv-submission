from openenv.core.http_env_client import HTTPEnvClient
from openenv.core.types import StepResult
from models import EmailTriageAction, EmailTriageObservation, EmailTriageState


class EmailTriageEnv(HTTPEnvClient[EmailTriageAction, EmailTriageObservation]):

    def _step_payload(self, action: EmailTriageAction) -> dict:
        return {
            "priority": action.priority,
            "category": action.category,
            "response": action.response,
        }

    def _parse_result(self, payload: dict) -> StepResult:
        return StepResult(
            observation=EmailTriageObservation(
                done=payload["done"],
                reward=payload.get("reward"),
                email_subject=payload.get("email_subject", ""),
                email_body=payload.get("email_body", ""),
                email_sender=payload.get("email_sender", ""),
                task_name=payload.get("task_name", ""),
                message=payload.get("message", ""),
            ),
            reward=payload.get("reward", 0.0),
            done=payload["done"],
        )

    def _parse_state(self, payload: dict) -> EmailTriageState:
        return EmailTriageState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_name=payload.get("task_name", ""),
        )