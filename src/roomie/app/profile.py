import uuid
from flask import Blueprint, jsonify, request
from . import storage
profiles_bp = Blueprint("profiles", __name__)
@profiles_bp.get("/profiles")
def get_profiles():
    profiles = storage.read_json("roommate_profiles.json")
    return jsonify(profiles), 200

@profiles_bp.get("/profiles/<profile_id>")
def get_profile(profile_id):
    profiles = storage.read_json("roommate_profiles.json")

    for profile in profiles:
        if profile.get("id") == profile_id:
            return jsonify(profile), 200

    return jsonify({"error": "Profile not found"}), 404

@profiles_bp.post("/profiles")
def create_profile():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400
    user_id = data.get("user_id")
    name = data.get("name")
    if not isinstance(user_id, str) or not user_id.strip():
        return jsonify({"error": "user_id is required"}), 400
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "name is required"}), 400
    budget = data.get("budget")
    if budget is not None and (
        isinstance(budget, bool)
        or not isinstance(budget, (int, float))
        or budget < 0
    ):
        return jsonify({"error": "budget must be a non-negative number"}), 400
    interests = data.get("interests", [])
    if not isinstance(interests, list) or not all(
        isinstance(interest, str) for interest in interests
    ):
        return jsonify({"error": "interests must be a list of strings"}), 400
    profile = {
        "id": str(uuid.uuid4()),
        "user_id": user_id.strip(),
        "name": name.strip(),
        "bio": data.get("bio", ""),
        "budget": budget,
        "preferred_location": data.get("preferred_location", ""),
        "interests": interests,
    }
    # Keep the read-modify-write operation together.
    with storage.storage_lock:
        profiles = storage.read_json("roommate_profiles.json")
        profiles.append(profile)
        storage.write_json("roommate_profiles.json", profiles)
    return jsonify(profile), 201