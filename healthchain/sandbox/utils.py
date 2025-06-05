import json
import logging

from pathlib import Path
from datetime import datetime


log = logging.getLogger(__name__)


def find_attributes_of_type(instance, target_type):
    """
    Find attributes of a specific type in an instance

    Args:
        instance: The object to inspect
        target_type: The type to look for

    Returns:
        List of attribute names matching the target type
    """
    attributes = []
    for attribute_name in dir(instance):
        attribute_value = getattr(instance, attribute_name)
        if isinstance(attribute_value, target_type):
            attributes.append(attribute_name)
    return attributes


def assign_to_attribute(instance, attribute_name, method_name, *args, **kwargs):
    """
    Call a method on an attribute of an instance

    Args:
        instance: Object containing the attribute
        attribute_name: Name of the attribute
        method_name: Method to call on the attribute
        *args, **kwargs: Arguments to pass to the method

    Returns:
        Result of the method call
    """
    attribute = getattr(instance, attribute_name)
    method = getattr(attribute, method_name)
    return method(*args, **kwargs)


def generate_filename(prefix: str, unique_id: str, index: int, extension: str):
    """
    Generate a filename with timestamp and unique identifier

    Args:
        prefix: Type of data (request, response)
        unique_id: Unique sandbox identifier
        index: Index number of the file
        extension: File extension (json, xml)

    Returns:
        Filename with timestamp and identifiers
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    filename = f"{timestamp}_sandbox_{unique_id[:8]}_{prefix}_{index}.{extension}"
    return filename


def save_file(data, prefix, sandbox_id, index, save_dir, extension):
    """
    Save data to a file

    Args:
        data: Data to save
        prefix: Type of data (request, response)
        sandbox_id: Unique sandbox identifier
        index: Index of the file
        save_dir: Directory to save to
        extension: File extension (json, xml)
    """
    save_name = generate_filename(prefix, str(sandbox_id), index, extension)
    file_path = save_dir / save_name
    if extension == "json":
        with open(file_path, "w") as outfile:
            json.dump(data, outfile, indent=4)
    elif extension == "xml":
        with open(file_path, "w") as outfile:
            outfile.write(data)
    else:
        raise ValueError(f"Unsupported extension: {extension}")


def ensure_directory_exists(directory):
    """
    Create directory if it doesn't exist

    Args:
        directory: Path to create

    Returns:
        Path object for created directory
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_data_to_directory(data_list, data_type, sandbox_id, save_dir, extension):
    """
    Save a list of data items to a directory

    Args:
        data_list: List of data to save
        data_type: Type of data (request, response)
        sandbox_id: Unique sandbox identifier
        save_dir: Directory to save to
        extension: File extension (json, xml)
    """
    for i, data in enumerate(data_list):
        try:
            save_file(data, data_type, sandbox_id, i, save_dir, extension)
        except Exception as e:
            log.warning(f"Error saving file {i} at {save_dir}: {e}")
