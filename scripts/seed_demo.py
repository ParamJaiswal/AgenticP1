#!/usr/bin/env python3
"""Seed demo data for testing AgenticP1.

Run: python scripts/seed_demo.py
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from datetime import datetime, timedelta
import random


async def seed():
    from app.db.database import init_db, AsyncSessionLocal
    from app.models.database import Organization
    from app.models.user import User
    from app.models.agent_config import AgentConfig
    from app.models.call import Call
    from app.models.conversation import ConversationTurn
    from app.api.middleware.auth_middleware import hash_password

    print("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Create demo org
        org = Organization(
            name="Demo Dental Clinic",
            slug="demo-dental-clinic",
            plan="growth",
            monthly_minutes_limit=2000,
        )
        db.add(org)
        await db.flush()

        # Create admin user
        user = User(
            organization_id=org.id,
            email="demo@agenticp1.com",
            hashed_password=hash_password("demo123456"),
            full_name="Demo Admin",
            role="admin",
        )
        db.add(user)
        await db.flush()

        # Create demo agent
        agent = AgentConfig(
            organization_id=org.id,
            name="Dental Support AI",
            description="AI agent for Demo Dental Clinic",
            industry="healthcare",
            personality="professional",
            greeting_message="Thank you for calling Demo Dental Clinic! How can I help you today?",
            tools_enabled={
                "book_appointment": True,
                "check_order_status": False,
                "transfer_to_human": True,
                "send_sms": True,
                "add_to_waitlist": True,
            },
            escalation_rules={
                "sentiment_threshold": -0.5,
                "max_turns_before_escalation": 10,
                "keywords": ["human", "manager", "supervisor"],
            },
            faqs=[
                {
                    "question": "What are your opening hours?",
                    "answer": "We are open Monday to Friday, 9 AM to 5 PM.",
                },
                {
                    "question": "Do you accept insurance?",
                    "answer": "Yes, we accept most major insurance plans.",
                },
                {
                    "question": "How do I book an appointment?",
                    "answer": "You can book an appointment over the phone, and I can help you right now!",
                },
            ],
        )
        db.add(agent)
        await db.flush()

        # Create sample calls
        sentiments = ["positive", "neutral", "negative"]
        resolutions = ["resolved", "escalated", "resolved", "resolved", "abandoned"]
        statuses = ["completed", "completed", "completed", "failed"]

        sample_callers = [
            "+15551001001", "+15551002002", "+15551003003",
            "+15551004004", "+15551005005", "+15551006006",
        ]

        for i in range(20):
            started = datetime.utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            duration = random.randint(60, 600)

            call = Call(
                organization_id=org.id,
                agent_id=agent.id,
                direction=random.choice(["inbound", "outbound"]),
                caller_number=random.choice(sample_callers),
                called_number="+15559001234",
                status=random.choice(statuses),
                started_at=started,
                ended_at=started + timedelta(seconds=duration),
                duration_seconds=duration,
                sentiment_score=round(random.uniform(-1, 1), 2),
                sentiment_label=random.choice(sentiments),
                resolution=random.choice(resolutions),
                summary="Customer called to book an appointment for a routine check-up.",
                cost_usd=round((duration / 60) * 0.005, 4),
            )
            db.add(call)
            await db.flush()

            # Sample transcript
            for turn_data in [
                ("assistant", "Thank you for calling Demo Dental Clinic! How can I help you today?"),
                ("user", "Hi, I'd like to book an appointment for next week."),
                ("assistant", "I'd be happy to help you book an appointment! What day works best for you?"),
                ("user", "Monday would be great."),
                ("assistant", "Perfect! I have Monday at 10 AM available. Shall I book that for you?"),
            ]:
                turn = ConversationTurn(
                    call_id=call.id,
                    role=turn_data[0],
                    content=turn_data[1],
                )
                db.add(turn)

        await db.commit()

    print("✅ Demo data seeded!")
    print("")
    print("Login credentials:")
    print("  Email:    demo@agenticp1.com")
    print("  Password: demo123456")


if __name__ == "__main__":
    asyncio.run(seed())
