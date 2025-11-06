"""
Enhanced Chatbot router for fraud detection with user data integration
Supports user info lookup, transaction history, and real-time fraud analysis
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Optional, List
import sqlite3
from pathlib import Path
from ..chatbot_nlp import chatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Database paths
USERS_DB = str(Path(__file__).resolve().parents[2] / "users.db")

class ChatMessage(BaseModel):
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    user_id: str

class UserInfo(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: Optional[str]
    created_at: Optional[str]
    transaction_count: int
    fraud_count: int
    total_amount: float

class TransactionInfo(BaseModel):
    id: int
    txn_time: str
    amount: float
    merchant: Optional[str]
    location: Optional[str]
    is_fraud: int
    description: Optional[str]

def get_users_db_conn():
    """Get connection to users.db"""
    conn = sqlite3.connect(USERS_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@router.post("/message", response_model=ChatResponse)
async def chat_message(chat: ChatMessage):
    """
    Process chatbot message and return response
    Enhanced with user data integration and real-time fraud analysis
    """
    try:
        response = chatbot.process_message(chat.user_id, chat.message)
        return ChatResponse(response=response, user_id=chat.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

@router.get("/user/{user_id}/info", response_model=UserInfo)
async def get_user_info(user_id: str):
    """Get comprehensive user information including transaction stats"""
    try:
        conn = get_users_db_conn()
        cur = conn.cursor()
        
        # Get user basic info
        cur.execute("""
            SELECT id, username, full_name, email, created_at 
            FROM users 
            WHERE username = ? OR id = ?
        """, (user_id, user_id))
        user_row = cur.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get transaction statistics
        cur.execute("""
            SELECT 
                COUNT(*) as transaction_count,
                SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
                SUM(amount) as total_amount
            FROM transactions 
            WHERE user_id = ?
        """, (user_row["id"],))
        stats_row = cur.fetchone()
        
        conn.close()
        
        return UserInfo(
            id=user_row["id"],
            username=user_row["username"],
            full_name=user_row["full_name"],
            email=user_row["email"],
            created_at=user_row["created_at"],
            transaction_count=stats_row["transaction_count"] or 0,
            fraud_count=stats_row["fraud_count"] or 0,
            total_amount=stats_row["total_amount"] or 0.0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/user/{user_id}/transactions", response_model=List[TransactionInfo])
async def get_user_transactions(
    user_id: str, 
    limit: int = Query(10, ge=1, le=100),
    include_fraud: bool = Query(True),
    min_amount: float = Query(0.0, ge=0)
):
    """Get user's transaction history with filtering options"""
    try:
        conn = get_users_db_conn()
        cur = conn.cursor()
        
        # First get user's database ID
        cur.execute("SELECT id FROM users WHERE username = ? OR id = ?", (user_id, user_id))
        user_row = cur.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build query with filters
        query = """
            SELECT id, txn_time, amount, merchant, location, is_fraud, description
            FROM transactions 
            WHERE user_id = ? AND amount >= ?
        """
        params = [user_row["id"], min_amount]
        
        if not include_fraud:
            query += " AND is_fraud = 0"
        
        query += " ORDER BY txn_time DESC LIMIT ?"
        params.append(limit)
        
        cur.execute(query, params)
        transactions = cur.fetchall()
        conn.close()
        
        return [TransactionInfo(**dict(t)) for t in transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/user/{user_id}/fraud-summary")
async def get_user_fraud_summary(user_id: str):
    """Get detailed fraud analysis for a user"""
    try:
        conn = get_users_db_conn()
        cur = conn.cursor()
        
        # Get user ID
        cur.execute("SELECT id, username, full_name FROM users WHERE username = ? OR id = ?", (user_id, user_id))
        user_row = cur.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get fraud statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_transactions,
                AVG(amount) as avg_amount,
                MAX(amount) as max_amount,
                SUM(CASE WHEN is_fraud = 1 THEN amount ELSE 0 END) as fraud_amount,
                COUNT(DISTINCT merchant) as unique_merchants
            FROM transactions 
            WHERE user_id = ?
        """, (user_row["id"],))
        stats = cur.fetchone()
        
        # Get recent fraud cases
        cur.execute("""
            SELECT txn_time, amount, merchant, location, description
            FROM transactions 
            WHERE user_id = ? AND is_fraud = 1
            ORDER BY txn_time DESC 
            LIMIT 5
        """, (user_row["id"],))
        recent_fraud = cur.fetchall()
        
        # Get spending patterns by merchant
        cur.execute("""
            SELECT 
                merchant,
                COUNT(*) as transaction_count,
                SUM(amount) as total_spent,
                SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count
            FROM transactions 
            WHERE user_id = ?
            GROUP BY merchant
            ORDER BY total_spent DESC
            LIMIT 10
        """, (user_row["id"],))
        merchant_patterns = cur.fetchall()
        
        conn.close()
        
        fraud_rate = (stats["fraud_transactions"] / max(stats["total_transactions"], 1)) * 100
        
        return {
            "user": {
                "username": user_row["username"],
                "full_name": user_row["full_name"]
            },
            "statistics": {
                "total_transactions": stats["total_transactions"],
                "fraud_transactions": stats["fraud_transactions"],
                "fraud_rate_percent": round(fraud_rate, 2),
                "avg_amount": round(stats["avg_amount"] or 0, 2),
                "max_amount": stats["max_amount"] or 0,
                "fraud_amount": stats["fraud_amount"] or 0,
                "unique_merchants": stats["unique_merchants"]
            },
            "recent_fraud_cases": [dict(f) for f in recent_fraud],
            "merchant_patterns": [dict(m) for m in merchant_patterns]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/session/{user_id}")
async def get_session_state(user_id: str):
    """Get current session state for a user"""
    if user_id in chatbot.session_state:
        return chatbot.session_state[user_id]
    return {"algorithm": "ann", "transaction_data": {}, "conversation_stage": "greeting"}

@router.delete("/session/{user_id}")
async def clear_session(user_id: str):
    """Clear session state for a user"""
    if user_id in chatbot.session_state:
        del chatbot.session_state[user_id]
    return {"message": "Session cleared"}

@router.get("/analytics/users-overview")
async def get_users_overview():
    """Get overview of all users and their fraud patterns"""
    try:
        conn = get_users_db_conn()
        cur = conn.cursor()
        
        # Get user statistics
        cur.execute("""
            SELECT 
                u.username,
                u.full_name,
                COUNT(t.id) as transaction_count,
                SUM(CASE WHEN t.is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
                SUM(t.amount) as total_amount,
                AVG(t.amount) as avg_amount
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            GROUP BY u.id, u.username, u.full_name
            ORDER BY fraud_count DESC, total_amount DESC
        """)
        users_stats = cur.fetchall()
        
        # Overall system statistics
        cur.execute("""
            SELECT 
                COUNT(DISTINCT user_id) as total_users,
                COUNT(*) as total_transactions,
                SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as total_fraud,
                SUM(amount) as total_volume,
                AVG(amount) as avg_transaction_amount
            FROM transactions
        """)
        system_stats = cur.fetchone()
        
        conn.close()
        
        users_data = []
        for user in users_stats:
            fraud_rate = (user["fraud_count"] / max(user["transaction_count"], 1)) * 100
            users_data.append({
                "username": user["username"],
                "full_name": user["full_name"],
                "transaction_count": user["transaction_count"],
                "fraud_count": user["fraud_count"],
                "fraud_rate_percent": round(fraud_rate, 2),
                "total_amount": round(user["total_amount"] or 0, 2),
                "avg_amount": round(user["avg_amount"] or 0, 2)
            })
        
        return {
            "system_overview": {
                "total_users": system_stats["total_users"],
                "total_transactions": system_stats["total_transactions"],
                "total_fraud": system_stats["total_fraud"],
                "system_fraud_rate": round((system_stats["total_fraud"] / max(system_stats["total_transactions"], 1)) * 100, 2),
                "total_volume": round(system_stats["total_volume"] or 0, 2),
                "avg_transaction_amount": round(system_stats["avg_transaction_amount"] or 0, 2)
            },
            "users": users_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")