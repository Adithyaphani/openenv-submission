 
import sys
import random
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

EMAILS = [
{"subject": "Payment failed 3 times", "body": "My payment has been declined three times today.", "sender": "angry.customer@example.com", "true_priority": "urgent", "true_category": "billing"},
{"subject": "Cannot login to account", "body": "I have been trying to login for 2 hours.", "sender": "user123@example.com", "true_priority": "urgent", "true_category": "technical"}
]

state = {"email": EMAILS[0], "task": "easy", "episode_id": "", "steps": 0}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset")
async def reset(request: Request):
    state["email"] = random.choice(EMAILS)
    state["episode_id"] = str(uuid.uuid4())
    return JSONResponse({"done": False})

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
