"""Promo code generation logic."""
import random
from typing import Set
from src.core.parse_api import promo_exists, create_promo_object


# Characters used for promo code suffix generation
_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"


def _gen_suffix(seen: Set[str]) -> str:
    """Generate a unique 4-character suffix for a promo code."""
    while True:
        s = "".join(random.choice(_CHARS) for _ in range(4))
        if s not in seen:
            seen.add(s)
            return s


def create_promo_for_user(user_id: str, prefix: str, duration: str, partner: str) -> str:
    """
    Generate and create a unique promo code for a user.
    
    Args:
        user_id: The user's email or phone number
        prefix: The promo code prefix (e.g., "AVZ-2DA-")
        duration: The duration of the promo (e.g., "LIFETIME", "30D")
        partner: The distribution partner (e.g., "AVAZ")
    
    Returns:
        The generated promo code
        
    Raises:
        RuntimeError: If a unique code cannot be generated after many attempts
    """
    uid = user_id.strip().lower()
    seen: Set[str] = set()
    
    for _ in range(100):  # retry on rare collisions
        code = f"{prefix}{_gen_suffix(seen)}"
        
        # If exists, try next code
        if promo_exists(code):
            continue
            
        payload = {
            "promoCodeId": code,
            "promoCodeDeviceCountLimit": 1,
            "promoCodeUser": uid,
            "promoCodeDuration": duration,
            "promoCodeDistributionPartner": partner,
        }
        create_promo_object(payload)
        return code
        
    raise RuntimeError("Could not generate a unique promo after many attempts")
