"""Online players endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from security import verify_api_key
from database import get_online_players

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/online-players", dependencies=[Depends(verify_api_key)])
async def get_online_players_endpoint():
    """Get list of currently online players"""
    try:
        players = get_online_players()
        return {
            "success": True,
            "count": len(players),
            "players": players
        }
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error fetching online players: {str(err)}")
