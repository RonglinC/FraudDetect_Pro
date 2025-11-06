import re
import json
import sqlite3
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
            'list transactions', 'my fraud', 'fraud history'
        ]
        text = text.lower()
        return any(keyword in text for keyword in history_keywords)

    def build_transaction_vector(self, amount: float, merchant: str = None, time: int = None) -> Dict[str, float]:
        # Create base vector with all required fields
        transaction = {
            "Time": time or 10000,  # Default time if not provided
            "Amount": amount,
        }
        
        # Add V1-V28 features (simplified - in real system these would be PCA components)
        # For demo, we'll use simple heuristics based on amount and merchant
        for i in range(1, 29):
            if i <= 14:
                # First half: amount-based features
                transaction[f"V{i}"] = (amount / 1000.0) * ((-1) ** i) * 0.1
            else:
                # Second half: merchant/time-based features  
                transaction[f"V{i}"] = 0.0
        
        # Adjust some features based on merchant (simplified merchant encoding)
        if merchant:
            merchant_lower = merchant.lower()
            if 'amazon' in merchant_lower:
                transaction["V14"] = -0.5
            elif 'starbucks' in merchant_lower:
                transaction["V14"] = 0.3
            elif any(term in merchant_lower for term in ['shell', 'gas', 'fuel']):
                transaction["V14"] = -1.2
        
        return transaction

    def call_ml_api(self, endpoint: str, data: Dict = None, algorithm: str = None) -> Dict:
        try:
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
                    
                    # Apply decision thresholds
                    if score < 0.25:
                        decision = "allow"
                    elif score < 0.60:
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
            else:
                return {"error": f"Unknown endpoint: {endpoint}"}
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
            
            greeting = f" **Welcome back, {name}!**\n\n"
            greeting += f"**Your Account Summary:**\n"
            greeting += f"• Total Transactions: {stats['transaction_count']}\n"
            greeting += f"• Fraud Rate: {stats['fraud_rate']}%\n"
            greeting += f"• Total Spent: ${stats['total_amount']:,.2f}\n\n"
        else:
            greeting = " **Welcome to FraudDetect Pro!**\n\n"
        
        greeting += """**What I can help you with:**

**Check Transactions**: "Check transaction for $500 at Amazon" 
**Your Info**: "Show my account info" or "My transaction history"
**Choose Algorithm**: "Use SVM" or "Switch to neural network"
**Analytics**: "Show my fraud cases" or "What algorithms are available?"

What would you like to do?"""
        
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
            response += "**Risk Assessment**: Some fraud detected - consider reviewing recent transactions.\n"
        else:
            response += "**Risk Assessment**: No fraud detected - account looks healthy!\n"
        
        response += "\nWould you like to see your recent transactions or check a specific transaction?"
        
        return response

    def _handle_transaction_history_request(self, user_id: str, message: str) -> str:
        # Check if user wants fraud-only
        fraud_only = any(word in message.lower() for word in ['fraud', 'suspicious', 'flagged'])
        limit = 5
        
        # Extract limit if specified
        limit_match = re.search(r'(?:last|recent)\s+(\d+)', message.lower())
        if limit_match:
            try:
                limit = min(int(limit_match.group(1)), 20) 
            except ValueError:
                pass
        
        transactions = self.get_user_transactions(user_id, limit, fraud_only)
        
        if not transactions:
            if fraud_only:
                return "Great news! You have no fraud cases in your transaction history."
            else:
                return "I couldn't find any transactions for your account."
        
        title = "**Recent Fraud Cases**" if fraud_only else f"**Your Last {len(transactions)} Transactions**"
        response = f"{title}\n\n"
        
        for i, txn in enumerate(transactions, 1):
            status = "FRAUD" if txn["is_fraud"] else "SAFE"
            time = txn["txn_time"][:16].replace('T', ' ')
            merchant = txn["merchant"] or "Unknown"
            location = txn["location"] or "Unknown location"
            
            response += f"**{i}.** {status} | ${txn['amount']:,.2f} at {merchant}\n"
            response += f"{location} | {time}\n"
            if txn["description"]:
                response += f"{txn['description']}\n"
            response += "\n"
        
        response += "Want me to analyze any of these transactions or check a new one?"
        
        return response

    def _handle_algorithm_selection(self, user_session: Dict, algorithm: str) -> str:
        try:
            # Set algorithm directly
            result = self.call_ml_api(f"/select/{algorithm}")
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
        
        # Get fraud score
        try:
            algorithm = user_session.get("algorithm", "ann")
            result = self.call_ml_api("/score", transaction_data, algorithm)
            
            if "error" in result:
                return f"Error analyzing transaction: {result['error']}"
            
            return self._format_fraud_response(result, amount, merchant, algorithm)
        except Exception as e:
            return f"Analysis failed: {str(e)}"

    def _format_fraud_response(self, result: Dict, amount: float, merchant: str, algorithm: str) -> str:
        score = result.get("score", 0)
        decision = result.get("decision", "unknown")
        confidence = result.get("confidence", 0)
        
        # Format merchant info
        merchant_info = f" at {merchant}" if merchant else ""
        
        # Create response based on decision
        if decision == "allow":
            status_text = "LEGITIMATE"
            advice = "This transaction appears safe to proceed."
            risk_level = "LOW RISK"
        elif decision == "challenge":
            status_text = "REQUIRES REVIEW"
            advice = "Additional verification recommended."
            risk_level = "MEDIUM RISK"
        else:  # block
            status_text = "HIGH RISK"
            advice = "This transaction should be blocked!"
            risk_level = "HIGH RISK"
        
        return f"""**Transaction Analysis Complete**

**Transaction**: ${amount:.2f}{merchant_info}
**Algorithm Used**: {algorithm.upper()}
**Risk Score**: {score:.1%}
**Decision**: {status_text}
**Risk Level**: {risk_level}

**Recommendation**: {advice}

**Analysis Details**:
• Confidence Level: {confidence:.1%}
• Model Version: {result.get('model_version', 'v1.0')}

Want to try a different algorithm or check another transaction?"""

    def _handle_algorithm_info(self) -> str:
        try:
            result = self.call_ml_api("/algorithms")
            if "error" in result:
                return f"Error getting algorithm info: {result['error']}"
            
            available = result.get("available", [])
            active = result.get("active", "unknown")
            
            algo_descriptions = {
                "ann": "**Neural Network** - Deep learning with multiple layers",
                "svm": "**Support Vector Machine** - High precision classification", 
                "knn": "**K-Nearest Neighbors** - Pattern matching algorithm"
            }
            
            response = f"**Currently Active**: {active.upper()}\n\n"
            response += "**Available ML Algorithms**:\n\n"
            
            for algo in ["ann", "svm", "knn"]:
                status = "Trained" if algo in available else "Not trained"
                desc = algo_descriptions.get(algo, "Machine learning classifier")
                response += f"**{algo.upper()}**: {desc}\n"
                response += f"Status: {status}\n\n"
            
            response += "**Switch algorithms by saying**:\n"
            response += "• 'Use SVM algorithm'\n"
            response += "• 'Switch to neural network'\n"
            response += "• 'Activate KNN'\n\n"
            response += "Want to see performance metrics for any algorithm?"
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def _default_response(self) -> str:
        return """I'm not sure how to help with that. Here's what I can do:

**Transaction Analysis**:
• "Check transaction for $200 at Target"
• "Is $1000 fraud?"
• "Analyze $50 purchase"

**Account Information**:
• "Show my account info"
• "My transaction history"
• "Show my fraud cases"

**Algorithm Management**:
• "Use SVM algorithm"
• "What algorithms are available?"
• "Show algorithm performance"

**Help & Info**:
• "Help" - Show this menu
• "Hello" - Restart conversation

What would you like to try?"""

# Global chatbot instance
chatbot = FraudDetectionChatbot()