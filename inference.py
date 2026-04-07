import os
import json
import textwrap
import urllib.request
import urllib.error
from typing import List
from openai import OpenAI

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or "dummy-key"
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK = "email-triage-env"
MAX_STEPS = 1
TASKS = ["easy", "medium", "hard"]
HF_SPACE_URL = "https://adithyaphani7-openenv-submission.hf.space"
SUCCESS_THRESHOLD = 0.1

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert customer support manager triaging emails.
    Given an email respond ONLY with a valid JSON object with exactly these fields:
    {"priority": "urgent" or "normal" or "low", "category": "billing" or "technical" or "general" or "spam", "response": "your professional reply here"}
    No extra text. No markdown. No code blocks. Only raw JSON.
"""^).strip^(^)


def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str^(success^).lower^(^)} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def call_env(endpoint, method="POST", body=None):
    url = f"{HF_SPACE_URL}/{endpoint}"
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[DEBUG] HTTP {e.code} error calling {endpoint}", flush=True)
        return {}
    except urllib.error.URLError as e:
        print(f"[DEBUG] URL error calling {endpoint}: {e.reason}", flush=True)
        return {}
    except Exception as e:
        print(f"[DEBUG] Unexpected error calling {endpoint}: {e}", flush=True)
        return {}


def get_action(client, obs):
    prompt = textwrap.dedent(f"""
        Email Subject: {obs.get('email_subject', 'No subject')}
        Email From: {obs.get('email_sender', 'unknown')}
        Email Body: {obs.get('email_body', 'No body')}
        Task: {obs.get('message', 'Triage this email')}
        Respond with JSON only.
    """^).strip^(^)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        text = completion.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        priority = data.get("priority", "normal")
        category = data.get("category", "general")
        response = data.get("response", "Thank you for contacting us. We will resolve this shortly.")
        if priority not in ["urgent", "normal", "low"]:
            priority = "normal"
        if category not in ["billing", "technical", "general", "spam"]:
            category = "general"
        return {"priority": priority, "category": category, "response": str(response)}
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON parse error: {e}", flush=True)
        return {"priority": "normal", "category": "general", "response": "Thank you for contacting us. We will resolve this shortly."}
    except Exception as e:
        print(f"[DEBUG] Model error: {e}", flush=True)
        return {"priority": "normal", "category": "general", "response": "Thank you for contacting us. We will resolve this shortly."}


def run_task(client, task_name):
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = call_env("reset", body={"task": task_name})
        if not result:
            print(f"[DEBUG] Empty response from reset", flush=True)
            log_end(success=False, steps=0, score=0.0, rewards=[0.0])
            return 0.0

        obs = result.get("observation", {})
        done = result.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = get_action(client, obs)
            action_str = f"priority={action['priority']},category={action['category']}"

            step_result = call_env("step", body=action)
            if not step_result:
                print(f"[DEBUG] Empty response from step", flush=True)
                reward = 0.0
                done = True
            else:
                obs = step_result.get("observation", {})
                reward = float(step_result.get("reward", 0.0) or 0.0)
                done = step_result.get("done", True)

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=None
            )

            if done:
                break

        if not rewards:
            rewards = [0.0]
            steps_taken = 1

        score = sum(rewards) / len(rewards)
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Unhandled error in run_task: {e}", flush=True)
        if not rewards:
            rewards = [0.0]
        if steps_taken == 0:
            steps_taken = 1
        score = 0.0
        success = False

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


def main():
    try:
        client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    except Exception as e:
        print(f"[DEBUG] Failed to create OpenAI client: {e}", flush=True)
        for task in TASKS:
            log_start(task=task, env=BENCHMARK, model=MODEL_NAME)
            log_step(step=1, action="priority=normal,category=general", reward=0.0, done=True, error=str(e))
            log_end(success=False, steps=1, score=0.0, rewards=[0.0])
        return

    for task in TASKS:
        run_task(client, task)


if __name__ == "__main__":
    main()
