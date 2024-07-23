from collections import deque
from typing import Dict, Optional


def search_key(dictionary: Dict, key: str) -> Optional[str]:
    if key in dictionary:
        return dictionary[key]

    for k, v in dictionary.items():
        if isinstance(v, dict):
            result = search_key(v, key)
            if result is not None:
                return result

    return None


def search_key_breadth_first(dictionary: Dict, key: str) -> Optional[str]:
    queue = deque([dictionary])

    while queue:
        current_dict = queue.popleft()

        if key in current_dict:
            return current_dict[key]

        for k, v in current_dict.items():
            if isinstance(v, dict):
                queue.append(v)

    return None


def insert_at_key(dictionary: Dict, key: str, value: str) -> bool:
    if key in dictionary:
        dictionary[key] = value
        return True

    for k, v in dictionary.items():
        if isinstance(v, dict):
            result = insert_at_key(v, key, value)
            if result:
                return True

    return False
