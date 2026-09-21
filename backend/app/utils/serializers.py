from datetime import datetime
from typing import Any, Dict, List
from bson import ObjectId


def serialize_mongo_doc(doc: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """
    Recursively serialize a MongoDB document converting `_id` to string `id`
    and ObjectIds/datetimes to JSON-compatible types.
    """
    if doc is None:
        return None

    result: Dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_mongo_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_mongo_doc(item) if isinstance(item, dict)
                else (str(item) if isinstance(item, ObjectId) else item)
                for item in value
            ]
        else:
            result[key] = value

    return result


def serialize_mongo_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize a list of MongoDB documents."""
    return [serialize_mongo_doc(doc) for doc in docs if doc is not None]  # type: ignore
