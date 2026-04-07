import sys
import random
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import subprocess

app = FastAPI()

EMAILS = [
    {"subject": "Payment failed 3 times", "body": "My payment has been declined three times. I need this resolved immediately.", "sender": "angry@example.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Cannot login to account", "body": "I have been trying to login for 2 hours. Password reset emails are not arriving.", "sender": "user123@example.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Question about pricing plans", "body": "Hi, I wanted to know about your premium plan pricing and features.", "sender": "prospect@example.com", "true_priority": "normal", "true_category": "general"},
    {"subject": "Invoice discrepancy", "body": "I was charged 150 dollars but my plan is 99 dollars. Please refund the difference.", "sender": "client@business.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Feature request: dark mode", "body": "It would be great if you could add dark mode to the dashboard.", "sender": "happyuser@example.com", "true_priority": "low", "true_category": "general"},
    {"subject": "API returning 500 errors", "body": "Your API keeps returning 500 errors. Our production app is completely down.", "sender": "dev@startup.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Win a free iPhone!!!", "body": "Click here to claim your prize. Limited time offer. Act now!!!", "sender": "spam@spam123.com", "true_priority": "low", "true_category": "spam"},
    {"subject": "Subscription renewal reminder", "body": "Your subscription renews in 7 days. No action needed if you wish to continue.", "sender": "billing@service.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "How do I export my data?", "body": "I cannot find how to export my data to CSV format in the documentation.", "sender": "user@company.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Thank you for great service", "body": "Your support team has been incredibly helpful this week. Keep up the great work!", "sender": "fan@example.com", "true_priority": "low", "true_category": "general"},
    {"subject": "URGENT: Account hacked", "body": "Someone accessed my account without permission. I need this locked immediately.", "sender": "victim@email.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Double charged this month", "body": "I have been charged twice for my monthly subscription. Please refund the duplicate.", "sender": "customer@gmail.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Integration with Slack broken", "body": "The Slack integration stopped working after your update yesterday.", "sender": "ops@techcorp.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Request for bulk discount", "body": "We are upgrading 50 seats to enterprise. Can you offer a volume discount?", "sender": "procurement@bigcorp.com", "true_priority": "normal", "true_category": "billing"},
    {"subject": "App crashes on iOS 17", "body": "Since updating to iOS 17 your mobile app crashes every time I open it.", "sender": "iphone@user.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Free crypto investment", "body": "Invest 100 dollars today and earn 10000 dollars guaranteed. Click now.", "sender": "invest@scam.io", "true_priority": "low", "true_category": "spam"},
    {"subject": "Service completely down", "body": "Your entire service is down. None of our 200 employees can access the platform.", "sender": "emergency@enterprise.com", "true_priority": "urgent", "true_category": "technical"},
    {"subject": "Wrong plan activated", "body": "I signed up for basic plan but was activated on premium and charged more.", "sender": "newuser@email.com", "true_priority": "urgent", "true_category": "billing"},
    {"subject": "Dashboard loading slowly", "body": "For 3 days the dashboard has been extremely slow. It takes 30 seconds to load.", "sender": "power@user.com", "true_priority": "normal", "true_category": "technical"},
    {"subject": "Cancel my subscription", "body": "I would like to cancel my subscription immediately and stop all future billing.", "sender": "leaving@customer.com", "true_priority": "normal", "true_category": "billing"},
]

DEFAULT_EMAIL = {"subject": "General inquiry", "body": "I have a question about your service.", "sender": "unknown@example.com", "true_priority": "normal", "true_category": "general"}

state = {"email": DEFAULT_EMAIL, "task": "easy", "episode_id": "", "steps": 0}


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
        state["task"] = body.get("task", "easy") if body else "easy"
        if state["task"] not in ["easy", "medium", "hard"]:
            state["task"] = "easy"
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
    except Exception as e:
        return JSONResponse({"observation": {}, "done": False, "info": {"error": str(e)}}, status_code=200)


@app.post("/step")
async def do_step(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        if not body:
            body = {}
        if not state["email"]:
            state["email"] = random.choice(EMAILS)
        state["steps"] += 1
        priority = str(body.get("priority", "normal"))
        category = str(body.get("category", "general"))
        response = str(body.get("response", ""))
        email = state["email"]
        task = state["task"]
        if task == "easy":
            priority_list = ["urgent", "normal", "low"]
            if priority == email["true_priority"]:
                reward = 1.0
            elif priority in priority_list and email["true_priority"] in priority_list and abs(priority_list.index(priority) - priority_list.index(email["true_priority"])) == 1:
                reward = 0.4
            else:
                reward = 0.0
        elif task == "medium":
            p = 1.0 if priority == email["true_priority"] else 0.0
            c = 1.0 if category == email["true_category"] else 0.0
            reward = round((p * 0.5) + (c * 0.5), 2)
        else:
            p = 1.0 if priority == email["true_priority"] else 0.0
            c = 1.0 if category == email["true_category"] else 0.0
            r = 0.0
            if len(response.strip()) >= 30:
                r += 0.4
            if any(k in response.lower() for k in ["thank", "help", "resolve", "assist", "support", "sorry", "understand"]):
                r += 0.3
            if response and response[0].isupper() and response.strip()[-1] in ".!?":
                r += 0.3
            reward = round((p * 0.3) + (c * 0.3) + (min(r, 1.0) * 0.4), 2)
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
    except Exception as e:
        return JSONResponse({"observation": {}, "reward": 0.0, "done": True, "info": {"error": str(e)}}, status_code=200)


@app.get("/state")
def get_state():
    try:
        return JSONResponse({"state": {"episode_id": state["episode_id"], "step_count": state["steps"], "task_name": state["task"]}})
    except Exception as e:
        return JSONResponse({"state": {}, "error": str(e)})


def main():
    subprocess.run(["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"])


if __name__ == "__main__":
    main()
