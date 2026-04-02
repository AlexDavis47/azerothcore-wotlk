import os
import secrets
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import mysql.connector
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    expected = os.getenv("SITE_API_KEY")
    if not expected or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=403, detail="Invalid API key")

def get_db_connection():
    """Create a MySQL connection"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/account/{username}", dependencies=[Depends(verify_api_key)])
async def get_account(username: str):
    """Get account info by username"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query account
        cursor.execute(
            "SELECT id, username FROM acore_auth.account WHERE username = %s",
            (username,)
        )
        account = cursor.fetchone()
        
        if not account:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Query characters for this account
        cursor.execute(
            "SELECT name, level, class, race FROM acore_characters.characters WHERE account = %s",
            (account['id'],)
        )
        characters = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "account": {
                "id": account['id'],
                "username": account['username']
            },
            "characters": characters
        }
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error: {str(err)}")

@app.post("/account", dependencies=[Depends(verify_api_key)])
async def create_account(username: str, password: str):
    """Create new WoW account"""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if account exists
        cursor.execute("SELECT id FROM acore_auth.account WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=409, detail="Account already exists")
        
        # Create account (this is a simple example - you may need to hash the password properly)
        cursor.execute(
            "INSERT INTO acore_auth.account (username, password) VALUES (%s, SHA2(%s, 256))",
            (username, password)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Account created successfully"
        }
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error: {str(err)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
