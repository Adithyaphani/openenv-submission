import sys
import random
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

EMAILS = [
    {"subject": "Payment failed", "body": "Payment declined 3 times.", "sender": "a@b.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Cannot login", "body": "Cannot login for 2 hours.", "sender": "b@c.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Pricing question", "body": "What is premium price?", "sender": "c@d.com", "true_priority": "normal", "true_category": "general"},
    {"subject": "Wrong invoice", "body": "Charged 150 but plan is 99.", "sender": "d@e.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Feature request", "body": "Please add dark mode.", "sender": "e@f.com", "true_priority": "low", "true_category": "general"},
    {"subject": "API is down", "body": "API returning 500 errors.", "sender": "f@g.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Win iPhone!", "body": "Click here now!!!", "sender": "g@h.com", "true_priority": "low", "true_category": "spam"},
]

state = {"email": EMAILS[0], "task": "easy", "episode_id": "", "steps": 0}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset")
async def reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    state["task"] = body.get("task", "easy") if body else "easy"
    state["email"] = random.choice(EMAILS)
    state["episode_id"] = str(uuid.uuid4())
    state["steps"] = 0
    return JSONResponse({
        "observation": {
            "email_subject": state["email"]["subject"],
            "email_body": state["email"]["body"],
            "email_sender": state["email"]["sender"],
            "task_name": state["task"],
            "message": "Triage this email.",
            "done": False,
            "reward": None
        },
        "done": False,
        "info": {}
    })

@app.post("/step")
async def do_step(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not body:
        body = {}
    state["steps"] += 1
    priority = body.get("priority", "normal")
    category = body.get("category", "general")
    response = body.get("response", "")
    email = state["email"]
    task = state["task"]
    if task == "easy":
        reward = 1.0 if priority == email["true_priority"] else 0.0
    elif task == "medium":
        p = 1.0 if priority == email["true_priority"] else 0.0
        c = 1.0 if category == email["true_category"] else 0.0
        reward = round((p * 0.5) + (c * 0.5), 2)
    else:
        p = 1.0 if priority == email["true_priority"] else 0.0
        c = 1.0 if category == email["true_category"] else 0.0
        r = 0.4 if len(response.strip()) >= 30 else 0.0
        if any(k in response.lower() for k in ["thank", "help", "resolve", "support"]):
            r += 0.3
        if response and response[0].isupper():
            r += 0.3
        reward = round((p*0.3)+(c*0.3)+(min(r,1.0)*0.4), 2)
    return JSONResponse({
        "observation": {
            "email_subject": email["subject"],
            "email_body": email["body"],
            "email_sender": email["sender"],
            "task_name": task,
            "message": "Scored.",
            "done": True,
            "reward": reward
        },
        "reward": reward,
        "done": True,
        "info": {}
    })

@app.get("/state")
def get_state():
    return JSONResponse({"state": {"episode_id": state["episode_id"], "step_count": state["steps"], "task_name": state["task"]}})

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
