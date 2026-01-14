from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    result = connection.execute(text("SELECT id, email, full_name, role FROM users"))
    users = result.fetchall()
    print(f"Found {len(users)} users:")
    for user in users:
        print(user)

    result = connection.execute(text("SELECT count(*) FROM departments"))
    print(f"Departments count: {result.scalar()}")
