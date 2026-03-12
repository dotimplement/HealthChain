from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union

from healthchain.interop.config_manager import InteropConfigManager


class BaseParser(ABC):
    """
    Abstract base class for parsers that convert healthcare data formats.
    """

    def __init__(self, config: InteropConfigManager):
        self.config = config

    @abstractmethod
    def from_string(self, data: str) -> dict:
        """
        Parse input data and convert it to a structured format.
        This method should be implemented by subclasses to handle specific formats.
        Args:
            data: The input data as a string

        Returns:
            A dictionary containing the parsed data structure
        """
        pass

    def from_bytes(self, data: bytes, encoding: str = "utf-8") -> dict:
        """Parse input data from bytes.

        Args:
            data: The input data as bytes
            encoding: Character encoding to use when decoding bytes

        Returns:
            A dictionary containing the parsed data structure
        """
        return self.from_string(data.decode(encoding))

    def from_file(self, file_path: Union[str, Path]) -> dict:
        """Parse input data from a file.

        Args:
            file_path: Path to the file to parse

        Returns:
            A dictionary containing the parsed data structure

        Raises:
            FileNotFoundError: If the file does not exist
        """
        path = Path(file_path)
        return self.from_string(path.read_text(encoding="utf-8"))

    def from_directory(
        self, directory_path: Union[str, Path], pattern: str = "*.xml"
    ) -> List[dict]:
        """Parse all matching files in a directory.

        Args:
            directory_path: Path to the directory containing files to parse
            pattern: Glob pattern to match files (default: "*.xml")

        Returns:
            A list of dictionaries, one per parsed file

        Raises:
            NotADirectoryError: If the path is not a directory
        """
        path = Path(directory_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        results = []
        for file_path in sorted(path.glob(pattern)):
            if file_path.is_file():
                results.append(self.from_file(file_path))
        return results
