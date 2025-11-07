import re
import json
import os
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from . import ml_models

class FraudDetectionChatbot:
    def __init__(self, backend_url: str = "http://127.0.0.1:8000"):
        self.backend_url = backend_url
        self.session_state = {}  # Will store user session data
        
        self.users_db_path = str(Path(__file__).resolve().parents[2] / "users.db")
        
        self.amount_patterns = [
            r'\$?(\d+(?:\.\d{2})?)',  # $123.45 or 123.45
            r'(\d+) dollars?',        # 123 dollars
            r'amount (?:of )?(\d+(?:\.\d{2})?)',  # amount of 123.45
        ]
        
        self.merchant_patterns = [
            r'(?:at|from|to) ([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # at Amazon, from Starbucks
            r'merchant (?:is )?([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # merchant Amazon
            r'purchased (?:from )?([A-Za-z]+(?:\s+[A-Za-z]+)?)',  # purchased from Target
        ]
        
        self.algorithm_patterns = {
            'ann': r'\b(?:ann|artificial neural network|neural|mlp)\b',
            'svm': r'\b(?:svm|support vector machine|vector)\b',
            'knn': r'\b(?:knn|k-nearest|nearest neighbor)\b'
        }
        
        # Common merchants for mapping
        self.merchant_map = {
            'amazon': 'Amazon', 'starbucks': 'Starbucks', 'target': 'Target',
            'walmart': 'Walmart', 'shell': 'Shell', 'uber': 'Uber',
            'apple': 'Apple', 'stripe': 'Stripe', 'mcdonalds': "McDonald's"
        }

    def get_db_connection(self):
        """Get connection to users database"""
        conn = sqlite3.connect(self.users_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get comprehensive user information from database"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Get user basic info
            cur.execute("""
                SELECT id, username, full_name, email, created_at 
                FROM users 
                WHERE username = ? OR id = ?
            """, (user_id, user_id))
            user_row = cur.fetchone()
            
            if not user_row:
                return None
            
            # Get transaction statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as transaction_count,
                    SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) as fraud_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    MAX(amount) as max_amount,
                    COUNT(DISTINCT merchant) as unique_merchants
                FROM transactions 
                WHERE user_id = ?
            """, (user_row["id"],))
            stats_row = cur.fetchone()
            
            conn.close()
            
            fraud_rate = (stats_row["fraud_count"] / max(stats_row["transaction_count"], 1)) * 100
            
            return {
                "id": user_row["id"],
                "username": user_row["username"],
                "full_name": user_row["full_name"],
                "email": user_row["email"],
                "created_at": user_row["created_at"],
                "stats": {
                    "transaction_count": stats_row["transaction_count"] or 0,
                    "fraud_count": stats_row["fraud_count"] or 0,
                    "fraud_rate": round(fraud_rate, 2),
                    "total_amount": round(stats_row["total_amount"] or 0, 2),
                    "avg_amount": round(stats_row["avg_amount"] or 0, 2),
                    "max_amount": stats_row["max_amount"] or 0,
                    "unique_merchants": stats_row["unique_merchants"] or 0
                }
            }
        except Exception as e:
            print(f"Database error getting user info: {e}")
            return None

    def get_user_transactions(self, user_id: str, limit: int = 5, fraud_only: bool = False) -> List[Dict]:
        """Get user's recent transactions"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Get user database ID
            cur.execute("SELECT id FROM users WHERE username = ? OR id = ?", (user_id, user_id))
            user_row = cur.fetchone()
            
            if not user_row:
                return []
            
            # Build query
            query = """
                SELECT txn_time, amount, merchant, location, is_fraud, description
                FROM transactions 
                WHERE user_id = ?
            """
            params = [user_row["id"]]
            
            if fraud_only:
                query += " AND is_fraud = 1"
            
            query += " ORDER BY txn_time DESC LIMIT ?"
            params.append(limit)
            
            cur.execute(query, params)
            transactions = cur.fetchall()
            conn.close()
            
            return [dict(t) for t in transactions]
        except Exception as e:
            print(f"Database error getting transactions: {e}")
            return []

    def extract_amount(self, text: str) -> Optional[float]:
        text = text.lower()
        for pattern in self.amount_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None

    def extract_merchant(self, text: str) -> Optional[str]:
        text = text.lower()
        for pattern in self.merchant_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                merchant = match.group(1).lower()
                return self.merchant_map.get(merchant, merchant.title())
        return None

    def detect_algorithm_selection(self, text: str) -> Optional[str]:
        text = text.lower()
        for algo, pattern in self.algorithm_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return algo
        return None

    def is_fraud_inquiry(self, text: str) -> bool:
        fraud_keywords = [
            'fraud', 'fraudulent', 'suspicious', 'check transaction',
            'is this fraud', 'analyze', 'score', 'legitimate', 'safe'
        ]
        text = text.lower()
        return any(keyword in text for keyword in fraud_keywords)

    def is_user_info_request(self, text: str) -> bool:
        info_keywords = [
            'my account', 'my profile', 'my info', 'my details', 'account info',
            'profile', 'who am i', 'my stats', 'my data', 'about me'
        ]
        text = text.lower()
        return any(keyword in text for keyword in info_keywords)

    def is_transaction_history_request(self, text: str) -> bool:
        history_keywords = [
            'my transactions', 'transaction history', 'recent transactions',
            'my purchases', 'spending history', 'show transactions',
            'list transactions', 'my fraud', 'fraud history',
            'transactions', 'transaction',  # Added simple keywords
            # Enhanced patterns for natural language
            'largest transaction', 'biggest transaction', 'highest transaction',
            'smallest transaction', 'lowest transaction', 'transaction review',
            'review transactions', 'analyze transactions', 'check transactions',
            'transaction summary', 'spending review', 'expense review',
            'do i have fraud', 'any fraud', 'fraud cases', 'show fraud',
            'fraud activity', 'fraudulent', 'suspicious activity'
        ]
        text = text.lower()
        return any(keyword in text for keyword in history_keywords)

    def build_transaction_vector(self, amount: float, merchant: str = None, time: int = None) -> Dict[str, float]:
        # Create base vector with all required fields
        transaction = {
            "Time": time or 10000,  # Default time if not provided
            "Amount": amount,
        }
        
        # Enhanced feature engineering for better fraud detection
        # V1-V28 features that are more sensitive to fraud patterns
        amount_log = np.log(max(amount, 0.01))  # Log transformation for amount
        
        for i in range(1, 29):
            if i <= 14:
                # Amount-based features with better fraud sensitivity
                if amount > 1000:  # High amount transactions
                    transaction[f"V{i}"] = (amount / 100.0) * ((-1) ** i) * 0.5
                elif amount < 1:  # Micro transactions (often fraud testing)
                    transaction[f"V{i}"] = amount * 10.0 * ((-1) ** i)
                else:
                    transaction[f"V{i}"] = amount_log * ((-1) ** i) * 0.2
            else:
                # Merchant and time-based features
                base_val = 0.1 if merchant else 0.0
                transaction[f"V{i}"] = base_val * ((-1) ** i)
        
        # Enhanced merchant-based risk scoring
        if merchant:
            merchant_lower = merchant.lower()
            # High-value merchants that are often targeted for fraud
            if 'starbucks' in merchant_lower and amount > 500:
                transaction["V14"] = 2.5  # Suspicious: High amount at coffee shop
                transaction["V15"] = 1.8
            elif 'uber' in merchant_lower and amount > 300:
                transaction["V16"] = 2.2  # Suspicious: High ride costs
            elif 'whole foods' in merchant_lower and amount < 20:
                transaction["V17"] = 1.5  # Suspicious: Very small grocery purchase
            elif any(term in merchant_lower for term in ['unknown', 'suspicious']):
                # Unknown merchants are high risk
                for j in range(20, 28):
                    transaction[f"V{j}"] = 1.0 + (j * 0.1)
        
        return transaction

    def call_ml_api(self, endpoint: str, method: str = "get", data: Dict = None, algorithm: str = None) -> Dict:
        """
        Unified API caller — works with local ML model or FastAPI backend.
        """

        try:
            # -------------------------
            # 1️⃣ LOCAL MODE (direct ml_models access)
            # -------------------------
            if endpoint == "/algorithms":
                available = ml_models.get_available_algorithms()
                return {
                    "algorithms": ["ann", "svm", "knn"],
                    "available": available,
                    "active": ml_models._active_algorithm
                }

            elif endpoint.startswith("/select/"):
                algo = endpoint.split("/")[-1]
                success = ml_models.set_active_algorithm(algo)
                if success:
                    return {
                        "status": "success",
                        "active_algorithm": algo,
                        "message": f"{algo.upper()} is now the active algorithm"
                    }
                else:
                    return {"error": f"Failed to activate {algo}"}

            elif endpoint == "/score":
                if not data:
                    return {"error": "No transaction data provided"}
                try:
                    result = ml_models.predict_fraud(data, algorithm)
                    score = result["score"]

                    # realistic fraud detection thresholds
                    if score < 0.01:
                        decision = "allow"
                    elif score < 0.05:
                        decision = "challenge"
                    else:
                        decision = "block"

                    return {
                        "score": score,
                        "decision": decision,
                        "algorithm": result["algorithm"],
                        "confidence": result["confidence"],
                        "model_version": "v1.0"
                    }
                except Exception as e:
                    return {"error": f"Scoring failed: {str(e)}"}

            elif endpoint == "/metrics":
                return ml_models.get_metrics(algorithm)

            # -------------------------
            # 2️⃣ REMOTE MODE (via FastAPI)
            # -------------------------
            else:
                import requests
                base_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
                url = f"{base_url}{endpoint}"

                if method.lower() == "post":
                    resp = requests.post(url, json=data or {}, timeout=10)
                else:
                    resp = requests.get(url, params=data or {}, timeout=10)

                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {"error": f"HTTP {resp.status_code}: {resp.text}"}

        except Exception as e:
            return {"error": f"ML operation failed: {str(e)}"}


    def process_message(self, user_id: str, message: str) -> str:
        message = message.strip()
        
        # Initialize user session if needed
        if user_id not in self.session_state:
            self.session_state[user_id] = {
                "algorithm": "ann",  # default
                "transaction_data": {},
                "conversation_stage": "greeting"
            }
        
        user_session = self.session_state[user_id]
        
        # Handle greetings and help
        if any(word in message.lower() for word in ['hello', 'hi', 'help', 'start']):
            return self._greeting_response(user_id)
        
        # Handle user info requests
        if self.is_user_info_request(message):
            return self._handle_user_info_request(user_id)
        
        # Handle transaction history requests
        if self.is_transaction_history_request(message):
            return self._handle_transaction_history_request(user_id, message)
        
        # Handle algorithm selection
        selected_algo = self.detect_algorithm_selection(message)
        if selected_algo:
            return self._handle_algorithm_selection(user_session, selected_algo)
        
        # Handle fraud detection requests
        if self.is_fraud_inquiry(message):
            return self._handle_fraud_inquiry(user_session, message)
        
        # Handle algorithm/model information requests
        if any(word in message.lower() for word in ['algorithm', 'model', 'available']):
            return self._handle_algorithm_info()
        
        # Default response with suggestions
        return self._default_response()

    def _greeting_response(self, user_id: str) -> str:
        user_info = self.get_user_info(user_id)
        
        if user_info:
            name = user_info["full_name"] or user_info["username"]
            stats = user_info["stats"]
            
            greeting = f"**Welcome back, {name}!**\n\n"
            greeting += f"**Your Account Summary:**\n"
            greeting += f"• Total Transactions: {stats['transaction_count']}\n"
            greeting += f"• Fraud Rate: {stats['fraud_rate']}%\n"
            greeting += f"• Total Spent: ${stats['total_amount']:,.2f}\n\n"
        else:
            greeting = "**Welcome to FraudDetect Pro!**\n\n"
            greeting += "**AI-Powered Fraud Detection Assistant**\n\n"
        
        greeting += """**Complete Command List:**

**Transaction History:**
  • "transactions" - Show recent transactions
  • "transaction history" - Show transaction list
  • "largest transaction" - Show biggest transaction
  • "smallest transaction" - Show smallest transaction
  • "transaction summary" - Complete spending analysis

**Fraud Detection:**
  • "fraud activity" - Show fraud cases only
  • "fraud cases" - Show detected fraud
  • "do i have fraud" - Check for fraud
  • "Check transaction for $500 at Amazon" - Analyze specific transaction
  • "Is $1000 fraud?" - Quick fraud check

**Account Information:**
  • "account info" - Show account details
  • "my account" - Show profile information
  • "my stats" - Show account statistics

**Algorithm Management:**
  • "Use SVM algorithm" - Switch to SVM
  • "Use neural network" - Switch to ANN
  • "Use KNN" - Switch to K-Nearest Neighbors
  • "What algorithms are available?" - Show algorithm options
  • "Show algorithm performance" - Display metrics

**Help & Navigation:**
  • "help" - Show this complete menu
  • "hello" - Restart conversation

What would you like to try?"""
        
        return greeting

    def _handle_user_info_request(self, user_id: str) -> str:
        user_info = self.get_user_info(user_id)
        
        if not user_info:
            return "Sorry, I couldn't find your account information. Please check if you're logged in correctly."
        
        stats = user_info["stats"]
        
        response = f"**Account Information for {user_info['full_name']}**\n\n"
        response += f"**Email**: {user_info['email']}\n"
        response += f"**Member Since**: {user_info['created_at'][:10]}\n\n"
        response += f"**Transaction Statistics**:\n"
        response += f"• Total Transactions: {stats['transaction_count']}\n"
        response += f"• Fraud Cases: {stats['fraud_count']}\n"
        response += f"• Fraud Rate: {stats['fraud_rate']}%\n"
        response += f"• Total Spent: ${stats['total_amount']:,.2f}\n"
        response += f"• Average Transaction: ${stats['avg_amount']:.2f}\n"
        response += f"• Largest Transaction: ${stats['max_amount']:,.2f}\n"
        response += f"• Unique Merchants: {stats['unique_merchants']}\n\n"
        
        if stats['fraud_count'] > 0:
            response += "**Risk Assessment**: Some fraud detected - consider reviewing your recent transactions on the homepage.\n"
        else:
            response += "**Risk Assessment**: No fraud detected - account looks healthy!\n"
        
        response += "\nI can help you analyze specific transactions or switch fraud detection algorithms. What would you like to do?"
        
        return response

    def _handle_transaction_history_request(self, user_id: str, message: str) -> str:
        # Check if user wants fraud-only
        message_lower = message.lower()
        fraud_only = any(word in message_lower for word in ['fraud', 'suspicious', 'flagged'])
        
        # Check for specific analysis types
        analysis_type = None
        if 'largest' in message_lower or 'biggest' in message_lower or 'highest' in message_lower:
            analysis_type = 'largest'
        elif 'smallest' in message_lower or 'lowest' in message_lower:
            analysis_type = 'smallest'
        elif 'review' in message_lower or 'summary' in message_lower or 'analyze' in message_lower:
            analysis_type = 'summary'
        
        limit = 10 if analysis_type else 5
        
        # Extract limit if specified
        limit_match = re.search(r'(?:last|recent)\s+(\d+)', message.lower())
        if limit_match:
            try:
                limit = min(int(limit_match.group(1)), 20) 
            except ValueError:
                pass
        
        transactions = self.get_user_transactions(user_id, limit, False)  # Always get all transactions first
        
        # Apply real-time fraud detection if looking for fraud cases
        if fraud_only:
            fraud_transactions = []
            for txn in transactions:
                real_time_score = self._apply_fraud_business_rules(
                    txn['amount'], 
                    txn['merchant'], 
                    0.01
                )
                if real_time_score >= 0.05:  # 5% fraud threshold
                    fraud_transactions.append(txn)
            transactions = fraud_transactions
        
        if not transactions:
            if fraud_only:
                return "Great news! You have no fraud cases in your transaction history."
            else:
                return "I couldn't find any transactions for your account."
        
        # Handle specific analysis requests
        if analysis_type == 'largest':
            largest_txn = max(transactions, key=lambda x: x['amount'])
            
            # Apply real-time fraud detection
            fraud_score = self._apply_fraud_business_rules(
                largest_txn['amount'], 
                largest_txn['merchant'], 
                0.01
            )
            is_fraud = fraud_score >= 0.05
            
            response = f"**Your Largest Transaction:**\n\n"
            status = "FRAUD" if is_fraud else "SAFE"
            time = largest_txn["txn_time"][:16].replace('T', ' ')
            merchant = largest_txn["merchant"] or "Unknown"
            location = largest_txn["location"] or "Unknown location"
            
            response += f"Status: {status}\n"
            response += f"Amount: ${largest_txn['amount']:,.2f}\n"
            response += f"Merchant: {merchant}\n"
            response += f"Location: {location}\n"
            response += f"Date: {time}\n"
            
            if is_fraud:
                response += f"**Fraud Risk: {fraud_score:.1%}**\n"
                if merchant and 'starbucks' in merchant.lower() and largest_txn['amount'] > 500:
                    response += f"**Alert**: ${largest_txn['amount']:,.2f} is extremely high for a coffee shop!\n"
            
            response += "\nWant me to analyze this transaction for fraud risk?"
            return response
            
        elif analysis_type == 'smallest':
            smallest_txn = min(transactions, key=lambda x: x['amount'])
            response = f"**Your Smallest Transaction:**\n\n"
            status = "FRAUD" if smallest_txn["is_fraud"] else "SAFE"
            time = smallest_txn["txn_time"][:16].replace('T', ' ')
            merchant = smallest_txn["merchant"] or "Unknown"
            location = smallest_txn["location"] or "Unknown location"
            
            response += f"Status: {status}\n"
            response += f"Amount: ${smallest_txn['amount']:,.2f}\n"
            response += f"Merchant: {merchant}\n"
            response += f"Location: {location}\n"
            response += f"Date: {time}\n"
            
            if smallest_txn['amount'] < 1:
                response += f"**Note**: Micro-transactions are sometimes used to test stolen cards.\n"
            
            response += "\nWant me to check more small transactions?"
            return response
            
        elif analysis_type == 'summary':
            total_amount = sum(t['amount'] for t in transactions)
            
            # Count real-time fraud cases instead of database flags
            fraud_count = 0
            fraud_amount = 0
            for txn in transactions:
                real_time_score = self._apply_fraud_business_rules(
                    txn['amount'], 
                    txn['merchant'], 
                    0.01
                )
                if real_time_score >= 0.05:  # 5% fraud threshold
                    fraud_count += 1
                    fraud_amount += txn['amount']
            
            avg_amount = total_amount / len(transactions) if transactions else 0
            
            response = f"**Transaction Analysis:**\n\n"
            response += f"Total Transactions: {len(transactions)}\n"
            response += f"Total Amount: ${total_amount:,.2f}\n"
            response += f"Average Amount: ${avg_amount:,.2f}\n"
            response += f"Fraud Cases: {fraud_count}\n"
            
            if fraud_count > 0:
                response += f"\n**Alert**: Found {fraud_count} fraudulent transaction(s)\n"
                response += f"Total Fraud Amount: ${fraud_amount:,.2f}\n"
            else:
                response += f"\n**Status**: No fraud detected in recent transactions\n"
            
            response += "\nWant detailed transaction list or specific analysis?"
            return response
        
        # Default transaction list
        title = "Recent Fraud Cases" if fraud_only else f"Your Last {len(transactions)} Transactions"
        response = f"**{title}**\n\n"
        
        for i, txn in enumerate(transactions, 1):
            # Apply real-time fraud detection to each transaction
            real_time_score = self._apply_fraud_business_rules(
                txn['amount'], 
                txn['merchant'], 
                0.01  # base score
            )
            
            # Determine if this should be flagged as fraud based on real rules
            is_real_fraud = real_time_score >= 0.05  # 5% threshold
            
            # Use real-time analysis instead of database flag
            status = "FRAUD" if is_real_fraud else "SAFE"
            time = txn["txn_time"][:16].replace('T', ' ')
            merchant = txn["merchant"] or "Unknown"
            location = txn["location"] or "Unknown location"
            
            response += f"{i}. {status} - ${txn['amount']:,.2f} at {merchant}\n"
            response += f"   {location} on {time}\n"
            
            # Add fraud analysis for high-risk transactions
            if is_real_fraud:
                response += f"   Fraud Risk: {real_time_score:.1%} - Review required!\n"
                
                # Specific fraud reasons
                if merchant and 'starbucks' in merchant.lower() and txn['amount'] > 500:
                    response += f"   Reason: Unusually high amount at coffee shop\n"
                elif txn['amount'] > 10000:
                    response += f"   Reason: Very high transaction amount\n"
                elif merchant and any(term in merchant.lower() for term in ['unknown', 'suspicious']):
                    response += f"   Reason: Unknown merchant\n"
            
            response += "\n"
        
        response += "Try: \"largest transaction\", \"transaction summary\", or ask about fraud!"
        
        return response

    def _handle_algorithm_selection(self, user_session: Dict, algorithm: str) -> str:
        try:
            # Set algorithm directly
            result = self.call_ml_api(f"/select/{algorithm}", method="post")
            if "error" in result:
                return f"Error selecting {algorithm.upper()}: {result['error']}"
            
            user_session["algorithm"] = algorithm
            
            # Get algorithm metrics
            metrics = self.call_ml_api("/metrics", None, algorithm)
            
            response = f"**Switched to {algorithm.upper()} Algorithm!**\n\n"
            
            if "error" not in metrics:
                response += f"**Performance Metrics:**\n"
                response += f"• Accuracy: {metrics.get('accuracy', 0)*100:.2f}%\n"
                response += f"• Precision: {metrics.get('precision', 0)*100:.2f}%\n"
                response += f"• Recall: {metrics.get('recall', 0)*100:.2f}%\n\n"
            
            response += "Now you can ask me to check transactions using this algorithm!"
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def _handle_fraud_inquiry(self, user_session: Dict, message: str) -> str:
        # Extract transaction details
        amount = self.extract_amount(message)
        merchant = self.extract_merchant(message)
        
        if not amount:
            return "I need the transaction amount. Try: 'Check transaction for $150' or 'Is $75 at Starbucks fraud?'"
        
        # Build transaction vector
        transaction_data = self.build_transaction_vector(amount, merchant)
        
        # Try ML model first, fallback to business rules if it fails
        try:
            algorithm = user_session.get("algorithm", "ann")
            result = self.call_ml_api("/score", transaction_data, algorithm)
            
            # If ML model fails, use business rules as fallback
            if "error" in result or "Model ann not loaded" in str(result):
                return self._handle_fraud_inquiry_fallback(amount, merchant, algorithm)
            
            # Enhanced fraud detection with business rules
            ml_score = result.get("score", 0)
            
            # Apply business rule enhancements for known fraud patterns
            enhanced_score = self._apply_fraud_business_rules(amount, merchant, ml_score)
            
            # Update result with enhanced score
            result["score"] = enhanced_score
            
            # Recalculate decision with new score
            if enhanced_score < 0.01:  # Less than 1%
                result["decision"] = "allow"
            elif enhanced_score < 0.05:  # 1-5%
                result["decision"] = "challenge" 
            else:  # Above 5%
                result["decision"] = "block"
            
            return self._format_fraud_response(result, amount, merchant, algorithm)
        except Exception as e:
            # Fallback to business rules if ML completely fails
            return self._handle_fraud_inquiry_fallback(amount, merchant, user_session.get("algorithm", "ann"))

    def _handle_fraud_inquiry_fallback(self, amount: float, merchant: str, algorithm: str) -> str:
        """Fallback fraud detection using only business rules"""
        # Apply business rules to get a base fraud score
        base_score = 0.01  # Default 1% risk for normal transactions
        enhanced_score = self._apply_fraud_business_rules(amount, merchant, base_score)
        
        # Create result dict
        result = {
            "score": enhanced_score,
            "algorithm": f"{algorithm} (business rules fallback)",
            "confidence": 0.85  # High confidence in business rules
        }
        
        # Determine decision
        if enhanced_score < 0.01:
            result["decision"] = "allow"
        elif enhanced_score < 0.05:
            result["decision"] = "challenge"
        else:
            result["decision"] = "block"
            
        return self._format_fraud_response(result, amount, merchant, algorithm)

    def _apply_fraud_business_rules(self, amount: float, merchant: str, base_score: float) -> float:
        """Apply business rules to enhance fraud detection"""
        score = base_score
        
        # Rule 1: High amounts at coffee shops (like the Starbucks case)
        if merchant and 'starbucks' in merchant.lower() and amount > 500:
            score = max(score, 0.08)  # 8% risk - requires review
            
        # Rule 2: Very high amounts at any merchant
        if amount > 10000:
            score = max(score, 0.06)  # 6% risk
            
        # Rule 3: Micro transactions (fraud testing)
        if amount < 0.1:
            score = max(score, 0.07)  # 7% risk
            
        # Rule 4: Unknown or suspicious merchants
        if merchant and any(term in merchant.lower() for term in ['unknown', 'suspicious']):
            score = max(score, 0.12)  # 12% risk - block
            
        # Rule 5: High ride sharing costs
        if merchant and 'uber' in merchant.lower() and amount > 300:
            score = max(score, 0.04)  # 4% risk
            
        # Rule 6: Unusual grocery amounts
        if merchant and 'whole foods' in merchant.lower():
            if amount < 5 or amount > 500:
                score = max(score, 0.03)  # 3% risk
        
        return min(score, 1.0)  # Cap at 100%

    def _format_fraud_response(self, result: Dict, amount: float, merchant: str, algorithm: str) -> str:
        score = result.get("score", 0)
        decision = result.get("decision", "unknown")
        confidence = result.get("confidence", 0)
        
        # Format merchant info
        merchant_info = f" at {merchant}" if merchant else ""
        
        # Create response based on decision with better formatting
        if decision == "allow":
            status_text = "LEGITIMATE"
            advice = "This transaction appears safe to proceed."
            risk_level = "LOW RISK"
            risk_color = "#28a745"
        elif decision == "challenge":
            status_text = "REQUIRES REVIEW"
            advice = "Additional verification recommended."
            risk_level = "MEDIUM RISK"
            risk_color = "#ffc107"
        else:  # block
            status_text = "BLOCKED"
            advice = "This transaction should be blocked immediately!"
            risk_level = "HIGH RISK"
            risk_color = "#dc3545"
        
        return f"""**Transaction Analysis Complete**

**Transaction Details**
• Amount: ${amount:.2f}{merchant_info}
• Algorithm: {algorithm.upper()}
• Risk Score: {score:.1%}

**Risk Assessment**
• Status: {status_text}
• Risk Level: {risk_level}
• Confidence: {confidence:.1%}

**Recommendation**
{advice}

**Technical Details**
• Model Version: {result.get('model_version', 'v1.0')}
• Analysis Time: Real-time

Want to analyze another transaction or try a different algorithm?"""

    def _handle_algorithm_info(self) -> str:
        try:
            result = self.call_ml_api("/algorithms")
            if "error" in result:
                return f"Error getting algorithm info: {result['error']}"
            
            available = result.get("available", [])
            active = result.get("active", "unknown")
            
            algo_descriptions = {
                "ann": "**Artificial Neural Network** - Deep learning with multiple layers for complex pattern recognition",
                "svm": "**Support Vector Machine** - High precision classification with optimal decision boundaries", 
                "knn": "**K-Nearest Neighbors** - Pattern matching algorithm based on similarity analysis"
            }
            
            response = f"**ML Algorithm Information**\n\n"
            response += f"**Currently Active**: {active.upper()}\n\n"
            response += "**Available Algorithms**:\n\n"
            
            for algo in ["ann", "svm", "knn"]:
                status_text = "Ready" if algo in available else "Not Available"
                desc = algo_descriptions.get(algo, "Machine learning classifier")
                response += f"{desc}\n"
                response += f"• Status: {status_text}\n\n"
            
            response += "**Switch Algorithms**:\n"
            response += "• 'Use SVM algorithm'\n"
            response += "• 'Switch to neural network'\n"
            response += "• 'Activate KNN'\n\n"
            response += "Want to see performance metrics for any algorithm?"
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def _default_response(self) -> str:
        return """I'm not sure how to help with that. Here's what I can do:

**Transaction History:**
  • "transactions" - Show recent transactions
  • "transaction history" - Show transaction list
  • "largest transaction" - Show biggest transaction
  • "smallest transaction" - Show smallest transaction
  • "transaction summary" - Complete spending analysis

**Fraud Detection:**
  • "fraud activity" - Show fraud cases only
  • "fraud cases" - Show detected fraud
  • "do i have fraud" - Check for fraud
  • "Check transaction for $500 at Amazon" - Analyze specific transaction
  • "Is $1000 fraud?" - Quick fraud check

**Account Information:**
  • "account info" - Show account details
  • "my account" - Show profile information
  • "my stats" - Show account statistics

**Algorithm Management:**
  • "Use SVM algorithm" - Switch to SVM
  • "Use neural network" - Switch to ANN
  • "Use KNN" - Switch to K-Nearest Neighbors
  • "What algorithms are available?" - Show algorithm options
  • "Show algorithm performance" - Display metrics

**Help & Navigation:**
  • "help" - Show this complete menu
  • "hello" - Restart conversation

What would you like to try?"""

# Global chatbot instance
chatbot = FraudDetectionChatbot()