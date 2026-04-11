import os
import json
import urllib.request
import urllib.error
from typing import List
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

BENCHMARK    = "email-triage-env"
HF_SPACE_URL = "https://adithyaphani7-openenv-submission.hf.space"
TASKS        = ["easy", "medium", "hard"]
MAX_STEPS    = 1

SYSTEM_PROMPT = (
    "You are an expert customer support manager triaging emails. "
    "Respond ONLY with a valid JSON object with exactly these fields: "
    "{priority: urgent or normal or low, "
    "category: billing or technical or general or spam, "
    "response: your professional reply here}. "
    "No extra text. No markdown. Only raw valid JSON."
)


def log_start(task, env, model):
    print("[START] task=" + task + " env=" + env + " model=" + model, flush=True)


def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    done_val  = "true" if done else "false"
    print("[STEP] step=" + str(step) + " action=" + action + " reward=" + format(reward, ".2f") + " done=" + done_val + " error=" + str(error_val), flush=True)


def log_end(success, steps, rewards):
    rewards_str = ",".join(format(r, ".2f") for r in rewards)
    success_val = "true" if success else "false"
    print("[END] success=" + success_val + " steps=" + str(steps) + " rewards=" + rewards_str, flush=True)


def call_env(endpoint, body=None):
    url  = HF_SPACE_URL + "/" + endpoint
    data = json.dumps(body or {}).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("[DEBUG] HTTP " + str(e.code) + " on /" + endpoint, flush=True)
        return {}
    except urllib.error.URLError as e:
        print("[DEBUG] URL error on /" + endpoint + ": " + str(e.reason), flush=True)
        return {}
    except Exception as e:
        print("[DEBUG] Error on /" + endpoint + ": " + str(e), flush=True)
        return {}


def get_action(client, obs):
    subject = obs.get("email_subject", "")
    sender  = obs.get("email_sender",  "")
    body    = obs.get("email_body",    "")
    message = obs.get("message",       "Triage this email.")
    prompt  = "Subject: " + subject + "\nFrom: " + sender + "\nBody: " + body + "\nTask: " + message + "\nJSON only:"
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
        raw = completion.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        priority = data.get("priority", "normal")
        category = data.get("category", "general")
        response = str(data.get("response", "Thank you for contacting us. We will resolve this soon."))
        if priority not in ["urgent", "normal", "low"]:
            priority = "normal"
        if category not in ["billing", "technical", "general", "spam"]:
            category = "general"
        return {"priority": priority, "category": category, "response": response}
    except Exception as e:
        print("[DEBUG] LLM error: " + str(e), flush=True)
        return {"priority": "normal", "category": "general", "response": "Thank you for contacting us. We will resolve this soon."}


def run_task(client, task_name):
    rewards     = []
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
            action      = get_action(client, obs)
            action_str  = "priority=" + action["priority"] + ",category=" + action["category"]
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
        print("[DEBUG] run_task error: " + str(e), flush=True)
        if not rewards:
            rewards = [0.01]
        if steps_taken == 0:
            steps_taken = 1
        success = False
    log_end(success=success, steps=steps_taken, rewards=rewards)


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    for task in TASKS:
        run_task(client, task)


if __name__ == "__main__":
    main()