import random
import uuid
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Email Triage Environment", version="1.0.0")

PRIORITY_LIST = ["urgent", "normal", "low"]
CATEGORY_LIST = ["billing", "technical", "general", "spam"]

EMAILS = [
    {"subject": "Payment failed 3 times", "body": "My payment has been declined three times. I need this resolved immediately.", "sender": "angry@example.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Cannot login to account", "body": "I have been trying to login for 2 hours. Password reset emails are not arriving.", "sender": "user123@example.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Question about pricing", "body": "Hi, I wanted to know about your premium plan pricing and features included.", "sender": "prospect@example.com", "true_priority": "normal", "true_category": "general"},
    {"subject": "Invoice discrepancy", "body": "I was charged 150 dollars but my plan is 99 dollars. Please refund the difference.", "sender": "client@business.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Feature request dark mode", "body": "It would be great if you could add dark mode to the dashboard.", "sender": "happyuser@example.com", "true_priority": "low", "true_category": "general"},
    {"subject": "API returning 500 errors", "body": "Your API keeps returning 500 errors. Our production app is completely down.", "sender": "dev@startup.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "You have won a prize", "body": "Click here to claim your prize. You have been selected as our lucky winner.", "sender": "spam@suspicious.net", "true_priority": "low", "true_category": "spam"},
    {"subject": "Subscription renewal", "body": "Your subscription renews in 7 days. No action needed if you wish to continue.", "sender": "billing@service.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "How to export data", "body": "I cannot find how to export my data to CSV format in the documentation.", "sender": "user@company.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Thank you for great service", "body": "Your support team has been incredibly helpful this week. Keep up the great work!", "sender": "fan@example.com", "true_priority": "low", "true_category": "general"},
    {"subject": "Account hacked urgent", "body": "Someone accessed my account without permission and changed my email. Lock it now.", "sender": "victim@email.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Double charged this month", "body": "I have been charged twice for my monthly subscription. Please refund the duplicate.", "sender": "customer@gmail.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Slack integration broken", "body": "The Slack integration stopped working after your update yesterday.", "sender": "ops@techcorp.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Bulk discount request", "body": "We are upgrading 50 seats to enterprise. Can you offer a volume discount?", "sender": "procurement@bigcorp.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "App crashes on iOS", "body": "Since updating to iOS 17 your mobile app crashes every time I open it.", "sender": "iphone@user.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Free crypto investment", "body": "Invest 100 dollars today and earn 10000 dollars guaranteed. Click now.", "sender": "invest@scam.io", "true_priority": "low", "true_category": "spam"},
    {"subject": "Service completely down", "body": "Your entire service is down. None of our 200 employees can access the platform.", "sender": "emergency@enterprise.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Wrong plan activated", "body": "I signed up for basic plan but was activated on premium and charged more.", "sender": "newuser@email.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Dashboard loading slowly", "body": "For 3 days the dashboard has been very slow. It takes over 30 seconds to load.", "sender": "power@user.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Cancel subscription", "body": "I would like to cancel my subscription immediately. Stop all future billing.", "sender": "leaving@customer.com", "true_priority": "normal", "true_category": "billing"},
]

DEFAULT_EMAIL = {"subject": "General inquiry", "body": "I have a question.", "sender": "user@example.com", "true_priority": "normal", "true_category": "general"}
STATE = {"email": DEFAULT_EMAIL, "task": "easy", "episode_id": str(uuid.uuid4()), "steps": 0}

MIN_REWARD = 0.05
MAX_REWARD = 0.95


def safe_reward(value):
    try:
        v = float(value)
    except Exception:
        v = MIN_REWARD
    if v <= 0.0 or v >= 1.0:
        v = MIN_REWARD
    return round(max(MIN_REWARD, min(MAX_REWARD, v)), 4)


def grade(email, task, priority, category, response):
    try:
        if priority not in PRIORITY_LIST:
            priority = "normal"
        if category not in CATEGORY_LIST:
            category = "general"

        if task == "easy":
            tp = PRIORITY_LIST.index(email["true_priority"])
            ap = PRIORITY_LIST.index(priority)
            if priority == email["true_priority"]:
                score = 0.90
            elif abs(tp - ap) == 1:
                score = 0.55
            else:
                score = MIN_REWARD

        elif task == "medium":
            p = 0.90 if priority == email["true_priority"] else MIN_REWARD
            c = 0.90 if category == email["true_category"] else MIN_REWARD
            score = (p * 0.5) + (c * 0.5)

        else:
            p = 0.90 if priority == email["true_priority"] else MIN_REWARD
            c = 0.90 if category == email["true_category"] else MIN_REWARD
            r = 0.0
            if len(response) >= 30:
                r = r + 0.40
            keywords = ["thank", "help", "resolve", "assist", "support", "sorry", "understand"]
            if any(k in response.lower() for k in keywords):
                r = r + 0.35
            if len(response) > 0 and response[0].isupper() and response[-1] in ".!?":
                r = r + 0.25
            r = min(r, 0.90)
            score = (p * 0.30) + (c * 0.30) + (r * 0.40)

        return safe_reward(score)

    except Exception:
        return MIN_REWARD


@app.get("/health")
def health():
    return {"status": "ok", "service": "email-triage-env"}


@app.post("/reset")
async def reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        task = body.get("task", "easy") if body else "easy"
        STATE["task"]       = task if task in ["easy", "medium", "hard"] else "easy"
        STATE["email"]      = random.choice(EMAILS)
        STATE["episode_id"] = str(uuid.uuid4())
        STATE["steps"]      = 0
        return JSONResponse({
            "observation": {
                "email_subject": STATE["email"]["subject"],
                "email_body":    STATE["email"]["body"],
                "email_sender":  STATE["email"]["sender"],
                "task_name":     STATE["task"],
                "message":       "Triage this email. Task: " + STATE["task"],
                "done":          False,
                "reward":        None
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
        body     = body or {}
        email    = STATE.get("email") or DEFAULT_EMAIL
        task     = STATE.get("task", "easy")
        priority = str(body.get("priority", "normal")).lower().strip()
        category = str(body.get("category", "general")).lower().strip()
        response = str(body.get("response", "")).strip()
        STATE["steps"] = STATE.get("steps", 0) + 1

        reward = grade(email, task, priority, category, response)

        return JSONResponse({
            "observation": {
                "email_subject": email["subject"],
                "email_body":    email["body"],
                "email_sender":  email["sender"],
                "task_name":     task,
                "message":       "Scored: " + str(reward),
                "done":          True,
                "reward":        reward
            },
            "reward": reward,
            "done":   True,
            "info":   {}
        })
    except Exception as e:
        return JSONResponse({
            "observation": {},
            "reward": MIN_REWARD,
            "done":   True,
            "info":   {"error": str(e)}
        }, status_code=200)


@app.get("/state")
def state():
    try:
        return JSONResponse({"state": {
            "episode_id": STATE.get("episode_id", ""),
            "step_count": STATE.get("steps", 0),
            "task_name":  STATE.get("task", "easy")
        }})
    except Exception as e:
        return JSONResponse({"state": {}, "error": str(e)})


def main():
    subprocess.run(["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"])


if __name__ == "__main__":
    main()