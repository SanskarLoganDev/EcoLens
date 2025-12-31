"""
CSV Transaction Parser
======================
Reads and validates transaction CSV files.

This module handles:
1. Reading CSV files with different encodings
2. Validating required columns exist
3. Cleaning and parsing data (dates, amounts)
4. Converting to structured Transaction objects

No AI used here - just data processing.
"""

from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, field_validator


class Transaction(BaseModel):
    """
    Single transaction model with validation.
    
    Pydantic automatically validates:
    - date must be a valid datetime
    - description must be a string
    - amount must be a float
    - category is optional (will be filled by Claude AI later)
    """
    date: datetime
    description: str
    amount: float
    category: Optional[str] = None
    
    @field_validator('amount')
    def amount_must_be_positive(cls, v):
        """Ensure transaction amounts are positive"""
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @field_validator('description')
    def description_not_empty(cls, v):
        """Ensure description is not empty"""
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()


class TransactionParser:
    """
    Parse transaction CSV files into validated Transaction objects.
    
    Example CSV format:
        date,description,amount
        2025-01-15,Delta Airlines,420.00
        2025-01-16,Starbucks,6.50
    """
    
    # Required columns in CSV
    REQUIRED_COLUMNS = ['date', 'description', 'amount']
    
    # Try these encodings in order (handles different CSV exports)
    SUPPORTED_ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    def __init__(self):
        """Initialize parser with empty transaction list"""
        self.transactions: List[Transaction] = []
        self.errors: List[str] = []  # Track any parsing errors
    
    def parse_csv(self, file_path: str) -> List[Transaction]:
        """
        Parse CSV file into Transaction objects.
        
        Process:
        1. Try different encodings to read file
        2. Validate required columns exist
        3. Parse dates and clean data
        4. Convert each row to Transaction object
        5. Skip invalid rows (but log them)
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of validated Transaction objects
            
        Raises:
            ValueError: If file can't be read or columns are missing
        """
        print(f"📄 Parsing CSV file: {file_path}")
        
        # Step 1: Read CSV with encoding detection
        df = self._read_csv_with_encoding(file_path)
        
        # Step 2: Validate required columns
        self._validate_columns(df)
        
        # Step 3: Clean and parse data
        df = self._clean_dataframe(df)
        
        # Step 4: Convert to Transaction objects
        transactions = self._convert_to_transactions(df)
        
        self.transactions = transactions
        
        print(f"✅ Successfully parsed {len(transactions)} transactions")
        if self.errors:
            print(f"⚠️  Skipped {len(self.errors)} invalid rows")
        
        return transactions
    
    def _read_csv_with_encoding(self, file_path: str) -> pd.DataFrame:
        """
        Try reading CSV with different encodings.
        
        Why: Different banks/systems export CSVs with different encodings.
        We try common ones until one works.
        """
        for encoding in self.SUPPORTED_ENCODINGS:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"  ✓ Read with {encoding} encoding")
                return df
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail
        raise ValueError(
            f"Could not read CSV with any supported encoding: {self.SUPPORTED_ENCODINGS}"
        )
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Check that all required columns are present.
        
        Required: date, description, amount
        Optional: category (we'll fill this with Claude later)
        """
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns)
        
        if missing_cols:
            raise ValueError(
                f"Missing required columns: {missing_cols}\n"
                f"Found columns: {list(df.columns)}\n"
                f"Required: {self.REQUIRED_COLUMNS}"
            )
        
        print(f"  ✓ All required columns present: {self.REQUIRED_COLUMNS}")
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize the data.
        
        Steps:
        1. Parse dates (handle multiple formats)
        2. Clean descriptions (remove extra spaces)
        3. Convert amounts to float
        4. Add empty category column if not present
        """
        # Parse dates - pandas tries to auto-detect format
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Clean descriptions (strip whitespace, uppercase for consistency)
        df['description'] = df['description'].astype(str).str.strip()
        
        # Ensure amount is float
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Add category column if not present
        if 'category' not in df.columns:
            df['category'] = None
        
        # Remove rows with any null values in required fields
        before_count = len(df)
        df = df.dropna(subset=['date', 'description', 'amount'])
        after_count = len(df)
        
        if before_count > after_count:
            print(f"  ⚠️  Removed {before_count - after_count} rows with missing data")
        
        return df
    
    def _convert_to_transactions(self, df: pd.DataFrame) -> List[Transaction]:
        """
        Convert DataFrame rows to Transaction objects.
        
        Uses Pydantic for validation - if a row is invalid,
        we log it and skip (don't crash the whole process).
        """
        transactions = []
        
        for index, row in df.iterrows():
            try:
                # Create Transaction object (Pydantic validates automatically)
                transaction = Transaction(
                    date=row['date'],
                    description=row['description'],
                    amount=row['amount'],
                    category=row.get('category')
                )
                transactions.append(transaction)
                
            except Exception as e:
                # Log error but continue processing
                error_msg = f"Row {index + 2}: {e}"  # +2 for 1-indexing and header
                self.errors.append(error_msg)
                print(f"  ⚠️  {error_msg}")
        
        return transactions
    
    def to_dict_list(self) -> List[Dict]:
        """
        Convert transactions to list of dictionaries.
        
        Useful for:
        - Sending to Claude API (needs JSON format)
        - Saving to database
        - Debugging/logging
        
        Returns:
            [
                {
                    'date': '2025-01-15',
                    'description': 'Delta Airlines',
                    'amount': 420.00,
                    'category': None
                },
                ...
            ]
        """
        return [
            {
                'date': t.date.isoformat(),
                'description': t.description,
                'amount': t.amount,
                'category': t.category
            }
            for t in self.transactions
        ]
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics about parsed transactions.
        
        Useful for quick sanity checks.
        """
        if not self.transactions:
            return {"error": "No transactions parsed"}
        
        dates = [t.date for t in self.transactions]
        amounts = [t.amount for t in self.transactions]
        
        return {
            'total_transactions': len(self.transactions),
            'total_amount': round(sum(amounts), 2),
            'average_amount': round(sum(amounts) / len(amounts), 2),
            'date_range': {
                'start': min(dates).strftime('%Y-%m-%d'),
                'end': max(dates).strftime('%Y-%m-%d'),
                'days': (max(dates) - min(dates)).days + 1
            },
            'errors_count': len(self.errors)
        }


# Example usage / testing
if __name__ == "__main__":
    """
    Test the parser with a sample CSV.
    
    Run this file directly to test:
        python parser.py
    """
    import json

    # Path to sample CSV (adjust as needed)
    csv_path = "src/services/carbon/samples/sample_transactions_5.csv"
    
    # Create parser instance
    parser = TransactionParser()
    
    # Parse the CSV
    try:
        print(f"\n📍 Step: Parsing CSV file: {csv_path}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   File exists: {Path(csv_path).exists()}")

        transactions = parser.parse_csv(csv_path)

        # Print summary
        print("\n📊 Summary:")
        summary = parser.get_summary()
        print(json.dumps(summary, indent=2))

        # Print first few transactions
        print("\n📝 First 3 transactions:")
        for t in transactions[:3]:
            print(f"  {t.date.strftime('%Y-%m-%d')} | {t.description[:30]:30} | ${t.amount:7.2f}")

        print("\n✅ Parser test complete!")

    except FileNotFoundError as e:
        print(f"\n❌ FileNotFoundError: {e}")
        print(f"\n📍 Location: File lookup failed")
        print(f"   File attempted: {csv_path}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   Absolute path: {Path(csv_path).absolute()}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ValueError as e:
        print(f"\n❌ ValueError: {e}")
        print(f"\n�� Location: Data validation failed")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        print(f"\n📍 Location: Missing required module")
        print("\nTip: Install dependencies with:")
        print("  pip install pandas pydantic")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ Unexpected error ({type(e).__name__}): {e}")
        print(f"\n📍 Location: Error details below")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()