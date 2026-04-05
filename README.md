---
title: Email Triage Environment
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Email Triage Environment

An OpenEnv RL environment where an AI agent triages customer support emails.

## Tasks
- **easy**: Classify email priority (urgent/normal/low)
- **medium**: Classify priority + category (billing/technical/general/spam)
- **hard**: Full triage — priority + category + draft response

## Action Space
- `priority`: urgent | normal | low
- `category`: billing | technical | general | spam
- `response`: string (draft reply)

## Observation Space
- `email_subject`: string
- `email_body`: string
- `email_sender`: string
- `task_name`: string
- `message`: task instruction

## Reward
- Easy: 1.0 (correct priority), 0.4 (adjacent), 0.0 (wrong)
- Medium: 0.5 × priority + 0.5 × category
- Hard: 0.3 × priority + 0.3 × category + 0.4 × response quality

## Setup
pip install openenv-core
