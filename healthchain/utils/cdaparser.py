import xmltodict
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


def search_key_from_xml_string(xml: str, key: str):
    xml_dict = xmltodict.parse(xml)

    return search_key(xml_dict, key)
