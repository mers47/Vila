import asyncio
import sys

from app.db.session import AsyncSessionLocal
from app.core.security import hash_password
from app.models.entities import User


async def create_admin(email: str, password: str):
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            print(f"User {email} already exists")
            return
        user = User(email=email, password_hash=hash_password(password), role="admin")
        db.add(user)
        await db.commit()
        print(f"Admin user {email} created")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_admin.py <email> <password>")
        sys.exit(1)
    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))