"""Database connection and query utilities"""
import os
import hashlib
import hmac
import mysql.connector
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
from fastapi import HTTPException


def get_db_connection():
    """Create and return a MySQL connection"""
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
        )
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(err)}")


def query_account(username: str) -> dict:
    """Query account by username from acore_auth database"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT id, username FROM acore_auth.account WHERE username = %s",
            (username,)
        )
        account = cursor.fetchone()
        return account
    finally:
        cursor.close()
        conn.close()


def query_characters(account_id: int) -> list:
    """Query characters for an account from acore_characters database"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT name, level, class, race FROM acore_characters.characters WHERE account = %s",
            (account_id,)
        )
        characters = cursor.fetchall()
        return characters
    finally:
        cursor.close()
        conn.close()


def account_exists(username: str) -> bool:
    """Check if account exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id FROM acore_auth.account WHERE username = %s",
            (username,)
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def _compute_srp6_verifier(username: str, password: str, salt: bytes) -> bytes:
    """
    Compute SRP6 verifier for account creation.
    Uses the same algorithm as AzerothCore/TrinityCore for WotLK.
    Based on WoWSimpleRegistration implementation.
    """
    # Convert username and password to uppercase as per WoW authentication
    username_password = (username.upper() + ':' + password.upper()).encode('utf-8')
    
    # Step 1: Calculate h1 = SHA1(USERNAME:PASSWORD)
    h1 = hashlib.sha1(username_password).digest()
    
    # Step 2: Calculate h2 = SHA1(salt + h1)
    h2 = hashlib.sha1(salt + h1).digest()
    
    # Step 3: Convert h2 to integer (little-endian)
    h2_int = int.from_bytes(h2, byteorder='little')
    
    # SRP6 parameters for WoW 3.3.5a (standard, not CMangos)
    # N is a 32-byte (256-bit) prime
    g = 7
    N = 0x894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7
    
    # Step 4: Compute verifier = g^h2 mod N
    verifier_int = pow(g, h2_int, N)
    
    # Step 5: Convert verifier back to bytes (little-endian, 32 bytes)
    verifier = verifier_int.to_bytes(32, byteorder='little')
    
    return verifier


def get_online_players() -> list:
    """Query all online players from acore_characters database"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            """SELECT c.name, c.race, c.class, c.gender, c.level, c.zone
               FROM acore_characters.characters c
               WHERE c.online = 1 AND c.deleteDate IS NULL
               ORDER BY c.name"""
        )
        players = cursor.fetchall()
        return players
    finally:
        cursor.close()
        conn.close()


def create_account(username: str, password: str) -> bool:
    """Create new WoW account with SRP6 authentication"""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    try:
        # Generate random salt (32 bytes)
        salt = os.urandom(32)
        
        # Compute SRP6 verifier
        verifier = _compute_srp6_verifier(username, password, salt)
        
        # Insert into database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO acore_auth.account 
                   (username, salt, verifier, email, reg_mail, expansion, locale) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (username, salt, verifier, '', '', 2, 0)  # expansion=2 (WotLK), locale=0 (enUS)
            )
            conn.commit()
            return True
        except mysql.connector.Error as err:
            conn.rollback()
            if "Duplicate entry" in str(err):
                raise HTTPException(status_code=409, detail="Account already exists")
            raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")
        finally:
            cursor.close()
            conn.close()
    
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error creating account: {str(err)}")
