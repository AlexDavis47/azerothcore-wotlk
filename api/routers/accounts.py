"""Account management endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from security import verify_api_key
from database import (
    query_account,
    query_characters,
    account_exists,
    create_account as db_create_account,
)

router = APIRouter(prefix="/account", tags=["accounts"])


class AccountCreate(BaseModel):
    """Account creation request model"""
    username: str = Field(..., min_length=3, max_length=32, description="Account username")
    password: str = Field(..., min_length=8, max_length=16, description="Account password")


class Account(BaseModel):
    """Account response model"""
    id: int
    username: str


@router.get("/{username}", dependencies=[Depends(verify_api_key)])
async def get_account(username: str):
    """Get account info by username including characters"""
    try:
        account = query_account(username)
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        characters = query_characters(account['id'])
        
        return {
            "success": True,
            "account": {
                "id": account['id'],
                "username": account['username']
            },
            "characters": characters
        }
    
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error: {str(err)}")


@router.post("/", dependencies=[Depends(verify_api_key)], status_code=201)
async def create_account(account: AccountCreate):
    """Create new WoW account with SRP6 authentication"""
    try:
        # Check if account already exists
        if account_exists(account.username):
            raise HTTPException(status_code=409, detail="Account already exists")
        
        # Create account with SRP6 authentication
        db_create_account(account.username, account.password)
        
        return {
            "success": True,
            "message": "Account created successfully",
            "username": account.username
        }
    
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error: {str(err)}")
