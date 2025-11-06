#!/usr/bin/env python3
"""
Create users.db and populate with fake users + transactions.
Run: python create_users_db.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
import uuid
import hashlib
DB_FILE = "users.db"

NUM_USERS = 8
TXNS_PER_USER = 30

def create_schema(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        created_at TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        txn_time TEXT NOT NULL,
        amount REAL NOT NULL,
        merchant TEXT,
        card_masked TEXT,
        location TEXT,
        is_fraud INTEGER DEFAULT 0,
        description TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()

def hash_password(plain: str) -> str:
    # Simple hash for demo (use bcrypt in production)
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def random_card_mask():
    # generate masked card like "XXXX-XXXX-XXXX-1234"
    last4 = str(random.randint(0, 9999)).zfill(4)
    return f"XXXX-XXXX-XXXX-{last4}"

def seed(conn):
    cur = conn.cursor()
    users = []
    # create sample users with known passwords so you can login in UI
    example_creds = [
        ("alice","Passw0rd!"),
        ("bob","Secur3P@ss"),
        ("carol","MyP0C123"),
        ("dave","Password123"),
        ("eve","TopSecret1"),
        ("frank","LetMeIn1"),
        ("grace","GracePwd!"),
        ("heidi","Heidi2025")
    ]
    for username, pwd in example_creds[:NUM_USERS]:
        full = f"{username.title()} Demo User"  # Simple name
        email = f"{username}@example.com"
        created_at = datetime.utcnow().isoformat()
        pwd_hash = hash_password(pwd)
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, pwd_hash, full, email, created_at)
        )
        users.append((cur.lastrowid, username, pwd))
    conn.commit()

    merchants = ["Amazon", "Starbucks", "Target", "Walmart", "Shell", "Uber", "Best Buy", "Stripe", "Apple", "Lyft", "Whole Foods"]
    for user_id, username, pwd in users:
        # generate transactions spanning past 90 days
        for i in range(TXNS_PER_USER):
            days_ago = random.randint(0, 90)
            seconds = random.randint(0, 24*3600)
            txn_dt = datetime.utcnow() - timedelta(days=days_ago, seconds=seconds)
            amount = round(random.uniform(1.5, 1200.0), 2)
            merchant = random.choice(merchants)
            card_mask = random_card_mask()
            location = "San Francisco, CA"  # Simple location
            is_fraud = 1 if (random.random() < 0.02) else 0  # ~2% labeled fraud
            desc = "Transaction processed"  # Simple description
            cur.execute(
                """INSERT INTO transactions
                (user_id, txn_time, amount, merchant, card_masked, location, is_fraud, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, txn_dt.isoformat(), amount, merchant, card_mask, location, is_fraud, desc)
            )
    conn.commit()
    print(f"Seeded {len(users)} users and {len(users)*TXNS_PER_USER} transactions into {DB_FILE}")
    print("Credentials (username:password) for testing:")
    for u in users:
        print(f"  {u[1]} : (see password in create script - generated as example)")

if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE, timeout=30)
    create_schema(conn)
    seed(conn)
    conn.close()
