import random
import uuid
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openenv.core.env_server import Environment
from models import EmailTriageAction, EmailTriageObservation, EmailTriageState

EMAILS = [
    {
        "subject": "URGENT: Payment failed 3 times",
        "body": "My payment has been declined three times today. I need this resolved immediately or I will cancel.",
        "sender": "angry.customer@example.com",
        "true_priority": "urgent",
        "true_category": "billing"
    },
    {
        "subject": "Cannot login to my account",
        "body": "I have been trying to login for 2 hours. Password reset is not working either.",
        "sender": "user123@example.com",
        "true_priority": "urgent",
        "true_category": "technical"
    },
    {
        "subject": "Question about pricing",
        "body": "Hi, I wanted to know about your premium plan pricing and what features are included.",
        "sender": "prospect@example.com",
        "true_priority": "normal",
        "true_category": "general"
    },
    {
        "subject": "Invoice discrepancy",
        "body": "I was charged $150 but my plan is $99. Please check and refund the difference.",
        "sender": "client@business.com",
        "true_priority": "urgent",
        "true_category": "billing"
    },
    {
        "subject": "Feature request",
        "body": "It would be great if you could add dark mode to the dashboard.",
        "sender": "happyuser@example.com",
        "true_priority": "low",
        "true_category": "general"
    },
    {
        "subject": "API integration not working",
        "body": "Your API keeps returning 500 errors on the /users endpoint. Our production app is down.",
        "sender": "dev@startup.com",
        "true_priority": "urgent",
        "true_category": "technical"
    },
    {
        "subject": "Win a free iPhone!!!",
        "body": "Click here to claim your prize. Limited time offer. Act now!!!",
        "sender": "noreply@spam123.com",
        "true_priority": "low",
        "true_category": "spam"
    },
    {
        "subject": "Subscription renewal reminder",
        "body": "Your subscription renews in 7 days. No action needed if you wish to continue.",
        "sender": "billing@ourservice.com",
        "true_priority": "normal",
        "true_category": "billing"
    },
    {
        "subject": "How do I export my data?",
        "body": "I have been looking through the docs but cannot find how to export my data to CSV.",
        "sender": "user@company.com",
        "true_priority": "normal",
        "true_category": "technical"
    },
    {
        "subject": "Thank you for great service",
        "body": "Just wanted to say your support team has been incredibly helpful. Keep up the great work!",
        "sender": "fan@example.com",
        "true_priority": "low",
        "true_category": "general"
    },
]

TASK_NAMES = ["easy", "medium", "hard"]


class EmailTriageEnvironment(Environment):

    def __init__(self, task_name: str = "easy"):
        self._task_name = task_name
        self._state = EmailTriageState()
        self._current_email = None

    def reset(self) -> EmailTriageObservation:
        self._state = EmailTriageState(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            task_name=self._task_name,
        )
        self._current_email = random.choice(EMAILS)

        if self._task_name == "easy":
            msg = "Task: Set the PRIORITY only (urgent/normal/low). Category and response can be empty."
        elif self._task_name == "medium":
            msg = "Task: Set PRIORITY (urgent/normal/low) AND CATEGORY (billing/technical/general/spam)."
        else:
            msg = "Task: Set PRIORITY, CATEGORY, and write a professional RESPONSE to this email."

        return EmailTriageObservation(
            done=False,
            reward=None,
            email_subject=self._current_email["subject"],
            email_body=self._current_email["body"],
            email_sender=self._current_email["sender"],
            task_name=self._task_name,
            message=msg,
        )

    def step(self, action: EmailTriageAction) -> EmailTriageObservation:
        self._state.step_count += 1
        reward = self._grade(action)
        return EmailTriageObservation(
            done=True,
            reward=reward,
            email_subject=self._current_email["subject"],
            email_body=self._current_email["body"],
            email_sender=self._current_email["sender"],
            task_name=self._task_name,
            message=f"Graded. Score: {reward:.2f}",
        )

    @property
    def state(self) -> EmailTriageState:
        return self._state

    def _grade(self, action: EmailTriageAction) -> float:
        email = self._current_email

        if self._task_name == "easy":
            if action.priority == email["true_priority"]:
                return 1.0
            adjacent = {
                "urgent": "normal",
                "normal": "urgent",
                "low": "normal",
            }
            if adjacent.get(action.priority) == email["true_priority"]:
                return 0.4
            return 0.0

        elif self._task_name == "medium":
            p = 1.0 if action.priority == email["true_priority"] else 0.0
            c = 1.0 if action.category == email["true_category"] else 0.0
            return round((p * 0.5) + (c * 0.5), 2)

        elif self._task_name == "hard":
            p = 1.0 if action.priority == email["true_priority"] else 0.0
            c = 1.0 if action.category == email["true_category"] else 0.0
            r = 0.0
            if len(action.response.strip()) >= 30:
                r += 0.4
            keywords = ["thank", "sorry", "help", "resolve",
                        "assist", "contact", "issue", "support"]
            if any(kw in action.response.lower() for kw in keywords):
                r += 0.3
            if action.response[0].isupper() and action.response.strip()[-1] in ".!?":
                r += 0.3
            return round((p * 0.3) + (c * 0.3) + (r * 0.4), 2)

        return 0.0