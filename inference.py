import asyncio
import os
import textwrap
from typing import List, Optional
from openai import OpenAI
from my_env.client import EmailTriageEnv, EmailTriageAction

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK = "email-triage-env"
MAX_STEPS = 1
TASKS = ["easy", "medium", "hard"]

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert customer support manager triaging emails.
    Given an email, respond ONLY with a JSON object with these fields:
    {
      "priority": "urgent" | "normal" | "low",
      "category": "billing" | "technical" | "general" | "spam",
      "response": "your draft reply here"
    }
    No extra text. Only valid JSON.
""").strip()


def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def get_action(client, obs) -> EmailTriageAction:
    prompt = f"""
Subject: {obs.email_subject}
From: {obs.email_sender}
Body: {obs.email_body}

Task: {obs.message}
"""
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
        import json
        text = completion.choices[0].message.content.strip()
        data = json.loads(text)
        return EmailTriageAction(
            priority=data.get("priority", "normal"),
            category=data.get("category", "general"),
            response=data.get("response", "Thank you for contacting us."),
        )
    except Exception as e:
        print(f"[DEBUG] Model error: {e}", flush=True)
        return EmailTriageAction(
            priority="normal",
            category="general",
            response="Thank you for contacting us. We will look into this.",
        )


async def run_task(client, task_name: str):
    env = EmailTriageEnv(base_url=f"http://localhost:7860", task=task_name)
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action = get_action(client, obs)
            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=f"priority={action.priority},category={action.category}",
                reward=reward,
                done=done,
                error=None,
            )

            if done:
                break

        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= 0.3

    finally:
        await env.close()
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    for task in TASKS:
        await run_task(client, task)


if __name__ == "__main__":
    asyncio.run(main())