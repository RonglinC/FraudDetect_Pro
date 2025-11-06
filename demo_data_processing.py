"""
Demo Credit Card Fraud Detection Data Processing Pipeline
From Sample Database Transaction Data to PCA Features (V1-V28)
Uses the fake transaction data created by create_user_db.py
"""

import pandas as pd
import numpy as np
import sqlite3
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, LabelEncoder
from datetime import datetime
import joblib
import os

class FraudDataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=28)
        self.label_encoders = {}
        self.is_fitted = False
    
    def load_transactions_from_db(self, db_path="users.db"):
        """Load transaction data from our sample database"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database {db_path} not found. Run create_user_db.py first!")
        
        conn = sqlite3.connect(db_path)
        
        # Load transactions with user info
        query = """
        SELECT 
            t.amount,
            t.txn_time as timestamp,
            t.merchant,
            t.location,
            t.card_masked,
            t.is_fraud,
            t.description,
            u.username,
            u.full_name,
            u.created_at as account_created
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.txn_time
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"Loaded {len(df)} transactions from database")
        print(f"Fraud transactions: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.1f}%)")
        
        return df
    
    def convert_db_to_raw_transactions(self, df):
        """Convert database format to our processing format"""
        transactions = []
        
        for _, row in df.iterrows():
            # Parse location
            location_parts = row['location'].split(', ')
            city = location_parts[0] if len(location_parts) > 0 else "Unknown"
            state_country = location_parts[1] if len(location_parts) > 1 else "Unknown"
            
            # Parse timestamp
            try:
                dt = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
            except:
                dt = datetime.now()
            
            # Calculate account age
            try:
                account_created = datetime.fromisoformat(row['account_created'].replace('Z', '+00:00'))
                account_age_days = (dt - account_created).days
            except:
                account_age_days = 365
            
            transaction = {
                'amount': float(row['amount']),
                'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'merchant': row['merchant'],
                'merchant_category': self.guess_merchant_category(row['merchant']),
                'city': city,
                'state': state_country,
                'country': 'US',  # Default for demo
                'card_type': 'Credit',  # Default for demo
                'card_brand': self.guess_card_brand(row['card_masked']),
                'user_age': 30,  # Default for demo
                'account_age_days': account_age_days,
                'user_avg_amount': 100.0,  # Will calculate later
                'recent_transactions': 1,  # Will calculate later
                'same_merchant_freq': 1,  # Will calculate later
                'hourly_velocity': 1,  # Will calculate later
                'is_fraud': row['is_fraud']
            }
            transactions.append(transaction)
        
        return transactions
    
    def guess_merchant_category(self, merchant):
        """Simple merchant category mapping"""
        categories = {
            'starbucks': 'Food & Dining',
            'mcdonald': 'Food & Dining', 
            'amazon': 'Online Retail',
            'target': 'Retail',
            'walmart': 'Retail',
            'shell': 'Gas Station',
            'uber': 'Transportation',
            'lyft': 'Transportation',
            'apple': 'Technology',
            'best buy': 'Electronics'
        }
        
        merchant_lower = merchant.lower()
        for key, category in categories.items():
            if key in merchant_lower:
                return category
        return 'Other'
    
    def guess_card_brand(self, card_masked):
        """Extract card brand from masked number (demo purposes)"""
        brands = ['Visa', 'Mastercard', 'American Express', 'Discover']
        return np.random.choice(brands)
    
    def extract_raw_features(self, transaction):
        """Extract features from raw transaction data"""
        dt = datetime.strptime(transaction['timestamp'], '%Y-%m-%d %H:%M:%S')
        
        features = {
            # Amount features
            'amount': float(transaction['amount']),
            'amount_log': np.log(max(transaction['amount'], 0.01)),
            
            # Time features
            'hour': dt.hour,
            'day_of_week': dt.weekday(),
            'day_of_month': dt.day,
            'month': dt.month,
            'is_weekend': 1 if dt.weekday() >= 5 else 0,
            'is_night': 1 if dt.hour < 6 or dt.hour > 22 else 0,
            
            # Merchant features
            'merchant': transaction.get('merchant', 'Unknown'),
            'merchant_category': transaction.get('merchant_category', 'Other'),
            
            # Location features
            'city': transaction.get('city', 'Unknown'),
            'state': transaction.get('state', 'Unknown'), 
            'country': transaction.get('country', 'US'),
            'is_international': 1 if transaction.get('country', 'US') != 'US' else 0,
            
            # Card features
            'card_type': transaction.get('card_type', 'Unknown'),
            'card_brand': transaction.get('card_brand', 'Unknown'),
            
            # User features
            'user_age': transaction.get('user_age', 30),
            'account_age_days': transaction.get('account_age_days', 365),
            
            # Behavioral features (would come from historical analysis)
            'avg_transaction_amount': transaction.get('user_avg_amount', 100.0),
            'transactions_last_24h': transaction.get('recent_transactions', 1),
            'same_merchant_count': transaction.get('same_merchant_freq', 0),
            'velocity_last_hour': transaction.get('hourly_velocity', 0),
        }
        
        return features
    
    def encode_categorical_features(self, df):
        """Convert categorical features to numerical"""
        categorical_columns = ['merchant', 'merchant_category', 'city', 'state', 
                             'country', 'card_type', 'card_brand']
        
        for col in categorical_columns:
            if col in df.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col].astype(str))
                else:
                    # Handle new categories during prediction
                    df[f'{col}_encoded'] = df[col].map(
                        dict(zip(self.label_encoders[col].classes_, 
                               self.label_encoders[col].transform(self.label_encoders[col].classes_)))
                    ).fillna(-1)  # Unknown category
        
        return df
    
    def engineer_advanced_features(self, df):
        """Create advanced engineered features"""
        # Amount-based features
        df['amount_vs_avg_ratio'] = df['amount'] / df['avg_transaction_amount']
        df['amount_zscore'] = (df['amount'] - df['avg_transaction_amount']) / (df['avg_transaction_amount'] * 0.5)
        
        # Time-based features  
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Frequency features
        df['transaction_frequency_score'] = df['transactions_last_24h'] / 24  # per hour
        df['merchant_familiarity'] = np.log(df['same_merchant_count'] + 1)
        
        # Risk features
        df['velocity_risk'] = df['velocity_last_hour'] / max(df['avg_transaction_amount'], 1)
        df['unusual_amount'] = (df['amount'] > df['avg_transaction_amount'] * 3).astype(int)
        df['round_amount'] = (df['amount'] % 100 == 0).astype(int)
        
        return df
    
    def prepare_feature_matrix(self, df):
        """Select numerical features for PCA"""
        # Select only numerical columns for PCA
        numerical_features = [
            'amount', 'amount_log', 'amount_vs_avg_ratio', 'amount_zscore',
            'hour', 'day_of_week', 'day_of_month', 'month', 'is_weekend', 'is_night',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'is_international', 'user_age', 'account_age_days',
            'transaction_frequency_score', 'merchant_familiarity', 'velocity_risk',
            'unusual_amount', 'round_amount', 'transactions_last_24h', 'same_merchant_count'
        ]
        
        # Add encoded categorical features
        encoded_features = [col for col in df.columns if col.endswith('_encoded')]
        all_features = numerical_features + encoded_features
        
        # Select available features
        available_features = [f for f in all_features if f in df.columns]
        
        return df[available_features].fillna(0)
    
    def fit_pca_transform(self, raw_transactions, labels=None):
        """Fit PCA on training data and transform to V1-V28 format"""
        # Convert to DataFrame
        feature_list = []
        for transaction in raw_transactions:
            features = self.extract_raw_features(transaction)
            feature_list.append(features)
        
        df = pd.DataFrame(feature_list)
        
        # Encode and engineer features
        df = self.encode_categorical_features(df)
        df = self.engineer_advanced_features(df)
        
        # Prepare feature matrix
        feature_matrix = self.prepare_feature_matrix(df)
        
        # Standardize features
        features_scaled = self.scaler.fit_transform(feature_matrix)
        
        # Apply PCA
        pca_features = self.pca.fit_transform(features_scaled)
        
        # Create V1-V28 format
        result = []
        for i, transaction in enumerate(raw_transactions):
            pca_dict = {f'V{j+1}': pca_features[i, j] for j in range(28)}
            pca_dict['Amount'] = transaction['amount']
            pca_dict['Time'] = i  # Simple time encoding
            result.append(pca_dict)
        
        self.is_fitted = True
        return result
    
    def transform_single_transaction(self, transaction):
        """Transform a single new transaction to V1-V28 format"""
        if not self.is_fitted:
            raise ValueError("Processor must be fitted first")
        
        # Extract and process features
        features = self.extract_raw_features(transaction)
        df = pd.DataFrame([features])
        df = self.encode_categorical_features(df)
        df = self.engineer_advanced_features(df)
        
        # Prepare feature matrix
        feature_matrix = self.prepare_feature_matrix(df)
        
        # Transform
        features_scaled = self.scaler.transform(feature_matrix)
        pca_features = self.pca.transform(features_scaled)
        
        # Return V1-V28 format
        result = {f'V{j+1}': pca_features[0, j] for j in range(28)}
        result['Amount'] = transaction['amount']
        result['Time'] = 10000  # Default time
        
        return result
    
    def save_processor(self, filepath):
        """Save fitted processor for later use"""
        joblib.dump({
            'scaler': self.scaler,
            'pca': self.pca,
            'label_encoders': self.label_encoders,
            'is_fitted': self.is_fitted
        }, filepath)
    
    def load_processor(self, filepath):
        """Load fitted processor"""
        data = joblib.load(filepath)
        self.scaler = data['scaler']
        self.pca = data['pca'] 
        self.label_encoders = data['label_encoders']
        self.is_fitted = data['is_fitted']

# Example usage with our sample database
if __name__ == "__main__":
    print("=== FRAUD DETECTION DATA PROCESSING DEMO ===")
    print("Converting sample database transactions to PCA format for ML models")
    
    try:
        # Initialize processor
        processor = FraudDataProcessor()
        
        # Load data from our sample database
        print("\n1. Loading transactions from sample database...")
        df = processor.load_transactions_from_db("users.db")
        
        # Convert to processing format
        print("\n2. Converting database format to processing format...")
        raw_transactions = processor.convert_db_to_raw_transactions(df)
        
        # Extract labels for training
        labels = [t['is_fraud'] for t in raw_transactions]
        print(f"   Total transactions: {len(raw_transactions)}")
        print(f"   Fraud cases: {sum(labels)} ({sum(labels)/len(labels)*100:.1f}%)")
        
        # Fit PCA and transform to V1-V28 format
        print("\n3. Applying feature engineering and PCA transformation...")
        pca_transactions = processor.fit_pca_transform(raw_transactions, labels)
        
        print(f"   Successfully transformed {len(pca_transactions)} transactions to V1-V28 format")
        
        # Show some examples
        print("\n4. Sample PCA-transformed transactions:")
        for i, trans in enumerate(pca_transactions[:3]):
            fraud_label = "FRAUD" if labels[i] else "LEGITIMATE"
            print(f"   Transaction {i+1} ({fraud_label}): V1={trans['V1']:.3f}, V14={trans['V14']:.3f}, Amount={trans['Amount']}")
        
        # Test single transaction processing
        print("\n5. Testing single transaction processing...")
        sample_transaction = raw_transactions[0]
        sample_transaction['amount'] = 500.0  # Modify for test
        
        pca_single = processor.transform_single_transaction(sample_transaction)
        print(f"   Single transaction PCA: V1={pca_single['V1']:.3f}, V14={pca_single['V14']:.3f}, Amount={pca_single['Amount']}")
        
        # Save processor for use with ML models
        print("\n6. Saving processor for ML model integration...")
        processor.save_processor('demo_fraud_processor.pkl')
        
        print("\n✅ SUCCESS: Sample database successfully converted to ML-ready format!")
        print("   - PCA processor saved to 'demo_fraud_processor.pkl'")
        print("   - Ready to integrate with chatbot and ML models")
        print("   - Can process new transactions in real-time")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("   Run: python3 backend/create_user_db.py first to create sample data")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("   Make sure all dependencies are installed")