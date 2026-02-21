"""Gamification Router - Badges, Challenges, Leaderboard, Streaks, Rewards Catalog
Expands the basic loyalty tier/points system with full gamification.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timedelta

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/gamification", tags=["gamification"])


# ============ BADGES ============
@router.get("/tenants/{tenant_slug}/badges")
async def list_badges(tenant_slug: str, user=Depends(get_current_user)):
    """List all badge definitions"""
    tenant = await resolve_tenant(tenant_slug)
    badges = await find_many_scoped("badges", tenant["id"], {}, sort=[("sort_order", 1)])
    return {"data": badges, "total": len(badges)}


@router.post("/tenants/{tenant_slug}/badges")
async def create_badge(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Create a new badge definition"""
    tenant = await resolve_tenant(tenant_slug)
    badge = await insert_scoped("badges", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "icon": data.get("icon", "star"),
        "color": data.get("color", "#FFD700"),
        "category": data.get("category", "general"),
        "criteria_type": data.get("criteria_type", "manual"),
        "criteria_value": data.get("criteria_value", 1),
        "criteria_event": data.get("criteria_event", ""),
        "points_reward": data.get("points_reward", 0),
        "sort_order": data.get("sort_order", 0),
        "active": True,
    })
    await log_audit(tenant["id"], "BADGE_CREATED", "badges", badge["id"], user.get("id", ""))
    return badge


@router.delete("/tenants/{tenant_slug}/badges/{badge_id}")
async def delete_badge(tenant_slug: str, badge_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("badges", tenant["id"], badge_id)
    await log_audit(tenant["id"], "BADGE_DELETED", "badges", badge_id, user.get("id", ""))
    return {"ok": True}


@router.get("/tenants/{tenant_slug}/members/{contact_id}/badges")
async def get_member_badges(tenant_slug: str, contact_id: str, user=Depends(get_current_user)):
    """Get all badges earned by a member"""
    tenant = await resolve_tenant(tenant_slug)
    earned = await find_many_scoped("earned_badges", tenant["id"],
                                     {"contact_id": contact_id},
                                     sort=[("earned_at", -1)])
    return {"data": earned, "total": len(earned)}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/award-badge")
async def award_badge(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    """Award a badge to a member"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    badge_id = data.get("badge_id", "")
    if not badge_id:
        raise HTTPException(status_code=400, detail="badge_id required")
    
    badge = await find_one_scoped("badges", tid, {"id": badge_id})
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    existing = await db.earned_badges.find_one({
        "tenant_id": tid, "contact_id": contact_id, "badge_id": badge_id
    })
    if existing:
        raise HTTPException(status_code=409, detail="Badge already earned")
    
    earned = await insert_scoped("earned_badges", tid, {
        "contact_id": contact_id,
        "badge_id": badge_id,
        "badge_name": badge.get("name", ""),
        "badge_icon": badge.get("icon", "star"),
        "badge_color": badge.get("color", "#FFD700"),
        "earned_at": now_utc().isoformat(),
        "awarded_by": user.get("id", ""),
    })
    
    # Award bonus points if badge has points_reward
    points_reward = badge.get("points_reward", 0)
    if points_reward > 0:
        acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
        if acct:
            new_balance = acct.get("points_balance", 0) + points_reward
            await db.loyalty_accounts.update_one(
                {"tenant_id": tid, "contact_id": contact_id},
                {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}}
            )
    
    # Create notification
    await insert_scoped("notifications", tid, {
        "type": "BADGE_EARNED",
        "title": f"Rozet Kazanildi: {badge.get('name', '')}",
        "body": f"{contact_id} yeni bir rozet kazandi: {badge.get('name', '')}",
        "entity_type": "badge",
        "entity_id": badge_id,
        "read": False,
        "priority": "normal",
    })
    
    await log_audit(tid, "BADGE_AWARDED", "earned_badges", earned["id"], user.get("id", ""))
    return earned


# ============ CHALLENGES ============
@router.get("/tenants/{tenant_slug}/challenges")
async def list_challenges(tenant_slug: str, status: Optional[str] = None, user=Depends(get_current_user)):
    """List all challenges"""
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    challenges = await find_many_scoped("challenges", tenant["id"], query, sort=[("created_at", -1)])
    return {"data": challenges, "total": len(challenges)}


@router.post("/tenants/{tenant_slug}/challenges")
async def create_challenge(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Create a new challenge"""
    tenant = await resolve_tenant(tenant_slug)
    challenge = await insert_scoped("challenges", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "type": data.get("type", "count"),
        "target_event": data.get("target_event", ""),
        "target_value": data.get("target_value", 1),
        "points_reward": data.get("points_reward", 50),
        "badge_reward_id": data.get("badge_reward_id", ""),
        "start_date": data.get("start_date", now_utc().isoformat()),
        "end_date": data.get("end_date", ""),
        "status": data.get("status", "active"),
        "participants_count": 0,
        "completions_count": 0,
    })
    await log_audit(tenant["id"], "CHALLENGE_CREATED", "challenges", challenge["id"], user.get("id", ""))
    return challenge


@router.patch("/tenants/{tenant_slug}/challenges/{challenge_id}")
async def update_challenge(tenant_slug: str, challenge_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["name", "description", "target_value", "points_reward", "end_date", "status"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await update_scoped("challenges", tenant["id"], challenge_id, update_data)
    return result


@router.delete("/tenants/{tenant_slug}/challenges/{challenge_id}")
async def delete_challenge(tenant_slug: str, challenge_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("challenges", tenant["id"], challenge_id)
    return {"ok": True}


@router.get("/tenants/{tenant_slug}/members/{contact_id}/challenge-progress")
async def get_challenge_progress(tenant_slug: str, contact_id: str, user=Depends(get_current_user)):
    """Get a member's progress on all active challenges"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    progress = await find_many_scoped("challenge_progress", tid,
                                       {"contact_id": contact_id},
                                       sort=[("updated_at", -1)])
    return {"data": progress, "total": len(progress)}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/challenge-progress")
async def update_challenge_progress(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    """Update progress on a challenge for a member"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    challenge_id = data.get("challenge_id", "")
    increment = data.get("increment", 1)
    
    challenge = await find_one_scoped("challenges", tid, {"id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    existing = await db.challenge_progress.find_one({
        "tenant_id": tid, "contact_id": contact_id, "challenge_id": challenge_id
    })
    
    if existing:
        new_val = existing.get("current_value", 0) + increment
        completed = new_val >= challenge.get("target_value", 1)
        await db.challenge_progress.update_one(
            {"tenant_id": tid, "contact_id": contact_id, "challenge_id": challenge_id},
            {"$set": {
                "current_value": new_val,
                "completed": completed,
                "completed_at": now_utc().isoformat() if completed and not existing.get("completed") else existing.get("completed_at", ""),
                "updated_at": now_utc().isoformat()
            }}
        )
        # Award points on completion
        if completed and not existing.get("completed"):
            await _award_challenge_completion(tid, contact_id, challenge)
        return {"current_value": new_val, "completed": completed, "target": challenge.get("target_value", 1)}
    else:
        completed = increment >= challenge.get("target_value", 1)
        await insert_scoped("challenge_progress", tid, {
            "contact_id": contact_id,
            "challenge_id": challenge_id,
            "challenge_name": challenge.get("name", ""),
            "current_value": increment,
            "target_value": challenge.get("target_value", 1),
            "completed": completed,
            "completed_at": now_utc().isoformat() if completed else "",
        })
        # Update participants count
        await db.challenges.update_one(
            {"tenant_id": tid, "id": challenge_id},
            {"$inc": {"participants_count": 1}}
        )
        if completed:
            await _award_challenge_completion(tid, contact_id, challenge)
        return {"current_value": increment, "completed": completed, "target": challenge.get("target_value", 1)}


async def _award_challenge_completion(tenant_id: str, contact_id: str, challenge: dict):
    """Award points and badge on challenge completion"""
    points = challenge.get("points_reward", 0)
    if points > 0:
        acct = await db.loyalty_accounts.find_one({"tenant_id": tenant_id, "contact_id": contact_id})
        if acct:
            new_balance = acct.get("points_balance", 0) + points
            await db.loyalty_accounts.update_one(
                {"tenant_id": tenant_id, "contact_id": contact_id},
                {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}}
            )
    # Update completions count
    await db.challenges.update_one(
        {"tenant_id": tenant_id, "id": challenge.get("id", "")},
        {"$inc": {"completions_count": 1}}
    )


# ============ LEADERBOARD ============
@router.get("/tenants/{tenant_slug}/leaderboard")
async def get_leaderboard(tenant_slug: str, period: str = "all_time", limit: int = 20,
                          user=Depends(get_current_user)):
    """Get leaderboard: top members by points"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    accounts = await find_many_scoped("loyalty_accounts", tid, {},
                                       sort=[("points_balance", -1)], limit=limit)
    
    leaderboard = []
    for rank, acct in enumerate(accounts, 1):
        contact = await find_one_scoped("contacts", tid, {"id": acct.get("contact_id", "")})
        badge_count = await count_scoped("earned_badges", tid, {"contact_id": acct.get("contact_id", "")})
        leaderboard.append({
            "rank": rank,
            "contact_id": acct.get("contact_id", ""),
            "contact_name": contact.get("name", "Unknown") if contact else "Unknown",
            "points": acct.get("points_balance", 0),
            "tier": acct.get("tier_name", "Silver"),
            "badge_count": badge_count,
            "enrolled_at": acct.get("enrolled_at", ""),
        })
    
    return {"data": leaderboard, "total": len(leaderboard), "period": period}


# ============ STREAKS ============
@router.get("/tenants/{tenant_slug}/members/{contact_id}/streaks")
async def get_member_streaks(tenant_slug: str, contact_id: str, user=Depends(get_current_user)):
    """Get member's active streaks"""
    tenant = await resolve_tenant(tenant_slug)
    streaks = await find_many_scoped("streaks", tenant["id"],
                                      {"contact_id": contact_id},
                                      sort=[("current_streak", -1)])
    return {"data": streaks, "total": len(streaks)}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/check-in")
async def record_checkin(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    """Record a check-in for streak tracking"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    streak_type = data.get("type", "daily_visit")
    
    existing = await db.streaks.find_one({
        "tenant_id": tid, "contact_id": contact_id, "streak_type": streak_type
    })
    
    now = now_utc()
    today = now.strftime("%Y-%m-%d")
    
    if existing:
        last_date = existing.get("last_check_in_date", "")
        if last_date == today:
            return {"message": "Already checked in today", "current_streak": existing.get("current_streak", 0)}
        
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_date == yesterday:
            new_streak = existing.get("current_streak", 0) + 1
            best = max(existing.get("best_streak", 0), new_streak)
        else:
            new_streak = 1
            best = existing.get("best_streak", 0)
        
        await db.streaks.update_one(
            {"tenant_id": tid, "contact_id": contact_id, "streak_type": streak_type},
            {"$set": {
                "current_streak": new_streak,
                "best_streak": best,
                "last_check_in_date": today,
                "total_check_ins": existing.get("total_check_ins", 0) + 1,
                "updated_at": now.isoformat(),
            }}
        )
        
        # Award bonus points for milestones
        if new_streak in [7, 30, 100]:
            bonus = {7: 50, 30: 200, 100: 1000}.get(new_streak, 0)
            acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
            if acct and bonus > 0:
                await db.loyalty_accounts.update_one(
                    {"tenant_id": tid, "contact_id": contact_id},
                    {"$inc": {"points_balance": bonus}}
                )
        
        return {"current_streak": new_streak, "best_streak": best, "check_in_date": today}
    else:
        await insert_scoped("streaks", tid, {
            "contact_id": contact_id,
            "streak_type": streak_type,
            "current_streak": 1,
            "best_streak": 1,
            "last_check_in_date": today,
            "total_check_ins": 1,
        })
        return {"current_streak": 1, "best_streak": 1, "check_in_date": today}


# ============ REWARDS CATALOG ============
@router.get("/tenants/{tenant_slug}/rewards")
async def list_rewards(tenant_slug: str, user=Depends(get_current_user)):
    """List all rewards in the catalog"""
    tenant = await resolve_tenant(tenant_slug)
    rewards = await find_many_scoped("rewards_catalog", tenant["id"], {},
                                      sort=[("points_cost", 1)])
    return {"data": rewards, "total": len(rewards)}


@router.post("/tenants/{tenant_slug}/rewards")
async def create_reward(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Create a new reward in the catalog"""
    tenant = await resolve_tenant(tenant_slug)
    reward = await insert_scoped("rewards_catalog", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "points_cost": data.get("points_cost", 100),
        "category": data.get("category", "general"),
        "icon": data.get("icon", "gift"),
        "stock": data.get("stock", -1),
        "redeemed_count": 0,
        "active": True,
    })
    await log_audit(tenant["id"], "REWARD_CREATED", "rewards_catalog", reward["id"], user.get("id", ""))
    return reward


@router.delete("/tenants/{tenant_slug}/rewards/{reward_id}")
async def delete_reward(tenant_slug: str, reward_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("rewards_catalog", tenant["id"], reward_id)
    return {"ok": True}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/redeem-reward")
async def redeem_reward(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    """Redeem a reward from the catalog"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    reward_id = data.get("reward_id", "")
    
    reward = await find_one_scoped("rewards_catalog", tid, {"id": reward_id})
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    if not reward.get("active", True):
        raise HTTPException(status_code=400, detail="Reward is not available")
    if reward.get("stock", -1) == 0:
        raise HTTPException(status_code=400, detail="Reward out of stock")
    
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    
    cost = reward.get("points_cost", 0)
    if acct.get("points_balance", 0) < cost:
        raise HTTPException(status_code=400, detail="Insufficient points")
    
    # Deduct points
    new_balance = acct["points_balance"] - cost
    await db.loyalty_accounts.update_one(
        {"tenant_id": tid, "contact_id": contact_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}}
    )
    
    # Update stock
    if reward.get("stock", -1) > 0:
        await db.rewards_catalog.update_one(
            {"tenant_id": tid, "id": reward_id},
            {"$inc": {"stock": -1, "redeemed_count": 1}}
        )
    else:
        await db.rewards_catalog.update_one(
            {"tenant_id": tid, "id": reward_id},
            {"$inc": {"redeemed_count": 1}}
        )
    
    # Record redemption
    redemption = await insert_scoped("reward_redemptions", tid, {
        "contact_id": contact_id,
        "reward_id": reward_id,
        "reward_name": reward.get("name", ""),
        "points_spent": cost,
        "status": "pending",
        "redeemed_at": now_utc().isoformat(),
    })
    
    await log_audit(tid, "REWARD_REDEEMED", "reward_redemptions", redemption["id"], user.get("id", ""))
    return {"redemption": redemption, "new_balance": new_balance}


@router.get("/tenants/{tenant_slug}/reward-redemptions")
async def list_redemptions(tenant_slug: str, status: Optional[str] = None,
                           page: int = 1, limit: int = 30, user=Depends(get_current_user)):
    """List all reward redemptions"""
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    skip = (page - 1) * limit
    redemptions = await find_many_scoped("reward_redemptions", tenant["id"], query,
                                          sort=[("redeemed_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("reward_redemptions", tenant["id"], query)
    return {"data": redemptions, "total": total, "page": page}


@router.patch("/tenants/{tenant_slug}/reward-redemptions/{redemption_id}")
async def update_redemption(tenant_slug: str, redemption_id: str, data: dict, user=Depends(get_current_user)):
    """Update redemption status (fulfilled/cancelled)"""
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["status", "notes"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    return await update_scoped("reward_redemptions", tenant["id"], redemption_id, update_data)


# ============ GAMIFICATION STATS ============
@router.get("/tenants/{tenant_slug}/stats")
async def get_gamification_stats(tenant_slug: str, user=Depends(get_current_user)):
    """Get overall gamification statistics"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    total_badges = await count_scoped("badges", tid)
    total_earned_badges = await count_scoped("earned_badges", tid)
    active_challenges = await count_scoped("challenges", tid, {"status": "active"})
    total_challenges = await count_scoped("challenges", tid)
    total_rewards = await count_scoped("rewards_catalog", tid, {"active": True})
    total_redemptions = await count_scoped("reward_redemptions", tid)
    total_members = await count_scoped("loyalty_accounts", tid)
    active_streaks = await count_scoped("streaks", tid)
    
    # Top badge earners
    pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {"_id": "$contact_id", "badge_count": {"$sum": 1}}},
        {"$sort": {"badge_count": -1}},
        {"$limit": 5}
    ]
    top_earners = []
    async for doc in db.earned_badges.aggregate(pipeline):
        top_earners.append({"contact_id": doc["_id"], "badge_count": doc["badge_count"]})
    
    return {
        "total_badges": total_badges,
        "total_earned_badges": total_earned_badges,
        "active_challenges": active_challenges,
        "total_challenges": total_challenges,
        "total_rewards": total_rewards,
        "total_redemptions": total_redemptions,
        "total_members": total_members,
        "active_streaks": active_streaks,
        "top_badge_earners": top_earners,
    }
