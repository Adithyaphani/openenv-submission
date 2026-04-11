import random
import uuid
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Email Triage Environment", version="1.0.0")

PRIORITY_LIST = ["urgent", "normal", "low"]
CATEGORY_LIST = ["billing", "technical", "general", "spam"]

EMAILS = [
    {"subject": "Payment failed 3 times", "body": "My payment has been declined three times today. I need this resolved immediately or I will cancel my account.", "sender": "angry@example.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Cannot login to account", "body": "I have been trying to login for 2 hours. Password reset emails are not arriving in my inbox either.", "sender": "user123@example.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Question about pricing plans", "body": "Hi, I wanted to know about your premium plan pricing and what features are included compared to basic.", "sender": "prospect@example.com", "true_priority": "normal", "true_category": "general"},
    {"subject": "Invoice discrepancy found", "body": "I was charged 150 dollars but my plan is only 99 dollars per month. Please check and refund the difference.", "sender": "client@business.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Feature request: dark mode", "body": "It would be great if you could add dark mode to the dashboard. Many users have been asking for this feature.", "sender": "happyuser@example.com", "true_priority": "low", "true_category": "general"},
    {"subject": "API returning 500 errors", "body": "Your API keeps returning 500 errors on the users endpoint. Our production application is completely down and we are losing revenue.", "sender": "dev@startup.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Congratulations you have won", "body": "Click here to claim your prize. You have been selected as our lucky winner. Send us your details now.", "sender": "spam@suspicious.net", "true_priority": "low", "true_category": "spam"},
    {"subject": "Subscription renewal reminder", "body": "Your subscription renews in 7 days. No action needed if you wish to continue. Contact us to make changes.", "sender": "billing@service.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "How do I export my data?", "body": "I cannot find how to export my data to CSV format in the documentation. Can you point me in the right direction?", "sender": "user@company.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Thank you for great service", "body": "Just wanted to say your support team has been incredibly helpful this week. Keep up the great work!", "sender": "fan@example.com", "true_priority": "low", "true_category": "general"},
    {"subject": "URGENT: Account hacked", "body": "Someone has accessed my account without permission and changed my email. I need this locked immediately.", "sender": "victim@email.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Double charged this month", "body": "I have been charged twice for my monthly subscription. Please refund the duplicate charge as soon as possible.", "sender": "customer@gmail.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Slack integration broken", "body": "The Slack integration stopped working after your update yesterday. Our team relies on these notifications daily.", "sender": "ops@techcorp.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Request for bulk discount", "body": "We are upgrading 50 seats to enterprise plan. Can you offer a volume discount for this purchase?", "sender": "procurement@bigcorp.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "App crashes on iOS 17", "body": "Since updating to iOS 17 your mobile app crashes every time I try to open it. This is very frustrating.", "sender": "iphone@user.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Free crypto investment now", "body": "Invest 100 dollars today and earn 10000 dollars in 30 days guaranteed. Click the link below to start.", "sender": "invest@scam.io", "true_priority": "low", "true_category": "spam"},
    {"subject": "Service completely down", "body": "Your entire service appears to be down. None of our 200 employees can access the platform right now.", "sender": "emergency@enterprise.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Wrong plan activated", "body": "I signed up for the basic plan but was activated on premium and charged the higher price. Please correct this.", "sender": "newuser@email.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Dashboard loading slowly", "body": "For the past 3 days the dashboard has been extremely slow to load. It takes over 30 seconds which is unusable.", "sender": "power@user.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Cancel my subscription now", "body": "I would like to cancel my subscription effective immediately. Please confirm and stop all future billing charges.", "sender": "leaving@customer.com", "true_priority": "normal", "true_category": "billing"},
]

DEFAULT_EMAIL = {"subject": "General inquiry", "body": "I have a question about your service.", "sender": "user@example.com", "true_priority": "normal", "true_category": "general"}
STATE = {"email": DEFAULT_EMAIL, "task": "easy", "episode_id": str(uuid.uuid4()), "steps": 0}


def clamp(value: float) -> float:
    return round(max(0.01, min(0.99, float(value))), 4)


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
        task = (body.get("task", "easy") if body else "easy")
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
                "message":       f"Triage this email. Task: {STATE['task']}",
                "done":          False,
                "reward":        None
            },
            "done":  False,
            "info":  {}
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
        email    = STATE.get("email", DEFAULT_EMAIL)
        task     = STATE.get("task", "easy")
        priority = str(body.get("priority", "normal")).lower().strip()
        category = str(body.get("category", "general")).lower().strip()
        response = str(body.get("response", "")).strip()
        STATE["steps"] += 1

        if priority not in PRIORITY_LIST:
            priority = "normal"
        if category not in CATEGORY_LIST:
            category = "general"

        if task == "easy":
            tp = PRIORITY_LIST.index(email["true_priority"])
            ap = PRIORITY_LIST.index(priority)
            if priority == email["true_priority"]:
                raw = 0.95
            elif abs(tp - ap) == 1:
                raw = 0.50
            else:
                raw = 0.05

        elif task == "medium":
            p   = 0.95 if priority == email["true_priority"] else 0.05
            c   = 0.95 if category == email["true_category"] else 0.05
            raw = (p * 0.5) + (c * 0.5)

        else:
            p = 0.95 if priority == email["true_priority"] else 0.05
            c = 0.95 if category == email["true_category"] else 0.05
            r = 0.0
            if len(response) >= 30:
                r += 0.40
            if any(k in response.lower() for k in ["thank","help","resolve","assist","support","sorry","understand","address"]):
                r += 0.35
            if response and response[0].isupper() and response[-1] in ".!?":
                r += 0.25
            raw = (p * 0.30) + (c * 0.30) + (min(r, 0.95) * 0.40)

        reward = clamp(raw)

        return JSONResponse({
            "observation": {
                "email_subject": email["subject"],
                "email_body":    email["body"],
                "email_sender":  email["sender"],
                "task_name":     task,
                "message":       f"Scored: {reward:.4f}",
                "done":          True,
                "reward":        reward
            },
            "reward": reward,
            "done":   True,
            "info":   {}
        })
    except Exception as e:
        return JSONResponse({"observation": {}, "reward": 0.05, "done": True, "info": {"error": str(e)}}, status_code=200)


@app.get("/state")
def state():
    try:
        return JSONResponse({"state": {
            "episode_id": STATE["episode_id"],
            "step_count": STATE["steps"],
            "task_name":  STATE["task"]
        }})
    except Exception as e:
        return JSONResponse({"state": {}, "error": str(e)})


def main():
    subprocess.run(["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"])

if __name__ == "__main__":
    main()
