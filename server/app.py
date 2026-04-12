import random
import uuid
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

PL = ["urgent", "normal", "low"]
CL = ["billing", "technical", "general", "spam"]
LO = 0.15
HI = 0.85

EMAILS = [
    {"subject": "Payment failed", "body": "My payment declined 3 times. Resolve immediately.", "sender": "a@b.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Cannot login", "body": "Cannot login for 2 hours. Password reset not working.", "sender": "b@c.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Pricing question", "body": "What is the premium plan pricing and features?", "sender": "c@d.com", "true_priority": "normal", "true_category": "general"},
    {"subject": "Invoice wrong", "body": "Charged 150 but plan is 99. Please refund.", "sender": "d@e.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Dark mode request", "body": "Please add dark mode to the dashboard.", "sender": "e@f.com", "true_priority": "low", "true_category": "general"},
    {"subject": "API 500 errors", "body": "API returning 500 errors. Production is down.", "sender": "f@g.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "You won a prize", "body": "Click here to claim your prize now.", "sender": "g@h.com", "true_priority": "low", "true_category": "spam"},
    {"subject": "Renewal reminder", "body": "Your subscription renews in 7 days.", "sender": "h@i.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "Export data help", "body": "Cannot find how to export data to CSV.", "sender": "i@j.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Great service thanks", "body": "Your support team has been very helpful.", "sender": "j@k.com", "true_priority": "low", "true_category": "general"},
    {"subject": "Account hacked", "body": "Someone changed my account email. Lock it now.", "sender": "k@l.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Double charged", "body": "Charged twice this month. Refund the duplicate.", "sender": "l@m.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Slack broken", "body": "Slack integration stopped after your update.", "sender": "m@n.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Bulk discount", "body": "Upgrading 50 seats. Can you offer a discount?", "sender": "n@o.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "App crashes iOS", "body": "App crashes every time since iOS 17 update.", "sender": "o@p.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Crypto investment", "body": "Invest 100 dollars earn 10000 guaranteed.", "sender": "p@q.com", "true_priority": "low", "true_category": "spam"},
    {"subject": "Service down", "body": "200 employees cannot access the platform.", "sender": "q@r.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Wrong plan", "body": "Activated on premium instead of basic.", "sender": "r@s.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Slow dashboard", "body": "Dashboard takes 30 seconds to load for 3 days.", "sender": "s@t.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Cancel subscription", "body": "Cancel my subscription and stop all billing.", "sender": "t@u.com", "true_priority": "normal", "true_category": "billing"},
]

DEF = {"subject": "Inquiry", "body": "Question.", "sender": "x@y.com", "true_priority": "normal", "true_category": "general"}
ST = {"email": DEF, "task": "easy", "episode_id": str(uuid.uuid4()), "steps": 0}


def sr(v):
    try:
        f = float(v)
    except Exception:
        return LO
    if f <= 0.0 or f >= 1.0:
        return LO
    r = max(LO, min(HI, round(f, 4)))
    if r <= 0.0 or r >= 1.0:
        return LO
    return r


def grade(email, task, priority, category, response):
    try:
        if priority not in PL:
            priority = "normal"
        if category not in CL:
            category = "general"
        if not isinstance(response, str):
            response = ""
        tp = PL.index(email.get("true_priority", "normal"))
        ap = PL.index(priority)
        tc = email.get("true_category", "general")
        if task == "easy":
            if priority == email.get("true_priority"):
                raw = 0.85
            elif abs(tp - ap) == 1:
                raw = 0.50
            else:
                raw = LO
        elif task == "medium":
            p = 0.85 if priority == email.get("true_priority") else LO
            c = 0.85 if category == tc else LO
            raw = (p * 0.5) + (c * 0.5)
        elif task == "hard":
            p = 0.85 if priority == email.get("true_priority") else LO
            c = 0.85 if category == tc else LO
            r = 0.0
            if len(response) >= 30:
                r += 0.35
            if any(k in response.lower() for k in ["thank", "help", "resolve", "support", "sorry"]):
                r += 0.30
            if len(response) > 0 and response[0].isupper() and response[-1] in ".!?":
                r += 0.20
            r = min(r, 0.80)
            raw = (p * 0.30) + (c * 0.30) + (r * 0.40)
        else:
            raw = LO
        return sr(raw)
    except Exception:
        return LO


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
async def reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        task = body.get("task", "easy") if body else "easy"
        ST["task"] = task if task in ["easy", "medium", "hard"] else "easy"
        ST["email"] = random.choice(EMAILS)
        ST["episode_id"] = str(uuid.uuid4())
        ST["steps"] = 0
        return JSONResponse({
            "observation": {
                "email_subject": ST["email"]["subject"],
                "email_body": ST["email"]["body"],
                "email_sender": ST["email"]["sender"],
                "task_name": ST["task"],
                "message": "Triage this email. Task: " + ST["task"],
                "done": False,
                "reward": None
            },
            "done": False,
            "info": {}
        })
    except Exception as e:
        return JSONResponse({"observation": {}, "done": False, "info": {"error": str(e)}}, status_code=200)


@app.post("/step")
async def step(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        body = body or {}
        email = ST.get("email") or DEF
        task = ST.get("task", "easy")
        priority = str(body.get("priority", "normal")).lower().strip()
        category = str(body.get("category", "general")).lower().strip()
        response = str(body.get("response", "")).strip()
        ST["steps"] = ST.get("steps", 0) + 1
        reward = grade(email, task, priority, category, response)
        if reward <= 0.0 or reward >= 1.0:
            reward = LO
        return JSONResponse({
            "observation": {
                "email_subject": email.get("subject", ""),
                "email_body": email.get("body", ""),
                "email_sender": email.get("sender", ""),
                "task_name": task,
                "message": "Score: " + str(reward),
                "done": True,
                "reward": reward
            },
            "reward": reward,
            "done": True,
            "info": {}
        })
    except Exception as e:
        return JSONResponse({"observation": {}, "reward": LO, "done": True, "info": {"error": str(e)}}, status_code=200)


@app.get("/state")
def state():
    try:
        return JSONResponse({"state": {
            "episode_id": ST.get("episode_id", ""),
            "step_count": ST.get("steps", 0),
            "task_name": ST.get("task", "easy")
        }})
    except Exception as e:
        return JSONResponse({"state": {}, "error": str(e)})


def main():
    subprocess.run(["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"])


if __name__ == "__main__":
    main()
