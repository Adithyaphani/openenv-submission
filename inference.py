import os
import json
import textwrap
import urllib.request
import urllib.error
from typing import List
from openai import OpenAI

# 컴 Environment Variables 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# 컴 Constants 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴�
BENCHMARK     = "email-triage-env"
HF_SPACE_URL  = "https://adithyaphani7-openenv-submission.hf.space"
TASKS         = ["easy", "medium", "hard"]
MAX_STEPS     = 1

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert customer support manager triaging emails.
    Respond ONLY with a valid JSON object with exactly these three fields:
    {
      "priority": "urgent" or "normal" or "low",
      "category": "billing" or "technical" or "general" or "spam",
      "response": "your professional reply to the email here"
    }
    No extra text. No markdown. No code blocks. Only raw valid JSON.
"""^).strip^(^)


# 컴 Logging 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴�
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error) -> None:
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str^(done^).lower^(^)} error={error_val}", flush=True)

def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str^(success^).lower^(^)} steps={steps} rewards={rewards_str}", flush=True)


# 컴 Environment HTTP Calls 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴
def call_env(endpoint: str, body: dict = None) -> dict:
    url  = f"{HF_SPACE_URL}/{endpoint}"
    data = json.dumps(body or {}).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[DEBUG] HTTP {e.code} on /{endpoint}", flush=True)
        return {}
    except urllib.error.URLError as e:
        print(f"[DEBUG] URL error on /{endpoint}: {e.reason}", flush=True)
        return {}
    except Exception as e:
        print(f"[DEBUG] Error on /{endpoint}: {e}", flush=True)
        return {}


# 컴 LLM Agent 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴
def get_action(client: OpenAI, obs: dict) -> dict:
    prompt = f"Subject: {obs.get^('email_subject',''^)}\nFrom: {obs.get^('email_sender',''^)}\nBody: {obs.get^('email_body',''^)}\nTask: {obs.get^('message','Triage this email.'^)}\nJSON only:"
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        raw  = completion.choices[0].message.content.strip()
        raw  = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        priority = data.get("priority", "normal")
        category = data.get("category", "general")
        response = str(data.get("response", "Thank you for contacting us. We will resolve this as soon as possible."))
        if priority not in ["urgent", "normal", "low"]:
            priority = "normal"
        if category not in ["billing", "technical", "general", "spam"]:
            category = "general"
        return {"priority": priority, "category": category, "response": response}
    except json.JSONDecodeError:
        return {"priority": "normal", "category": "general", "response": "Thank you for contacting us. We will resolve this as soon as possible."}
    except Exception as e:
        print(f"[DEBUG] LLM error: {e}", flush=True)
        return {"priority": "normal", "category": "general", "response": "Thank you for contacting us. We will resolve this as soon as possible."}


# 컴 Task Runner 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴
def run_task(client: OpenAI, task_name: str) -> None:
    rewards: List[float] = []
    steps_taken = 0
    success     = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = call_env("reset", {"task": task_name})
        if not result:
            log_end(success=False, steps=1, rewards=[0.01])
            return

        obs  = result.get("observation", {})
        done = result.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action     = get_action(client, obs)
            action_str = f"priority={action['priority']},category={action['category']}"

            step_result = call_env("step", action)
            if not step_result:
                reward = 0.01
                done   = True
            else:
                obs    = step_result.get("observation", {})
                reward = float(step_result.get("reward", 0.01) or 0.01)
                done   = step_result.get("done", True)

            reward = round(max(0.01, min(0.99, reward)), 4)
            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=None)

            if done:
                break

        if not rewards:
            rewards     = [0.01]
            steps_taken = 1

        success = (sum(rewards) / len(rewards)) >= 0.1

    except Exception as e:
        print(f"[DEBUG] run_task error: {e}", flush=True)
        if not rewards:
            rewards = [0.01]
        if steps_taken == 0:
            steps_taken = 1
        success = False

    log_end(success=success, steps=steps_taken, rewards=rewards)


# 컴 Entry Point 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴
def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    for task in TASKS:
        run_task(client, task)

if __name__ == "__main__":
    main()
