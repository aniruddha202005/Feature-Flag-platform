"""Create a handful of demo flags. Usage: python scripts/seed.py [base_url]"""

import sys

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

FLAGS = [
    {
        "key": "new-checkout",
        "name": "New checkout flow",
        "description": "Single-page checkout replacing the 3-step wizard.",
        "enabled": True,
        "rollout_percentage": 25,
        "targeted_users": ["qa_team_1", "qa_team_2"],
    },
    {
        "key": "dark-mode",
        "name": "Dark mode",
        "description": "Dark theme across the web app.",
        "enabled": True,
        "rollout_percentage": 100,
    },
    {
        "key": "upi-autopay",
        "name": "UPI AutoPay",
        "description": "Recurring UPI mandates, India only.",
        "enabled": True,
        "rollout_percentage": 0,
        "rules": [{"attribute": "country", "operator": "equals", "values": ["IN"]}],
    },
    {
        "key": "ai-recommendations",
        "name": "AI product recommendations",
        "description": "LLM-ranked recommendations for paid plans.",
        "enabled": False,
        "rollout_percentage": 10,
        "rules": [{"attribute": "plan", "operator": "in", "values": ["pro", "enterprise"]}],
    },
]


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=5) as client:
        for flag in FLAGS:
            response = client.post("/api/v1/flags", json=flag)
            if response.status_code == 409:
                print(f"skip   {flag['key']} (already exists)")
            else:
                response.raise_for_status()
                print(f"create {flag['key']}")


if __name__ == "__main__":
    main()
