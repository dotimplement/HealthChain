from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator
import logging

from healthchain.interop.config_manager import InteropConfigManager

log = logging.getLogger(__name__)


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

    def from_file(self, file_path: str) -> dict:
        """
        Read a file and parse its contents.

        Args:
            file_path: Path to the file to parse

        Returns:
            A dictionary containing the parsed data structure

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file is empty
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        log.debug(f"Parsing file: {file_path}")
        data = path.read_text(encoding="utf-8")

        if not data.strip():
            raise ValueError(f"File is empty: {file_path}")

        return self.from_string(data)

    def from_directory(
        self,
        directory_path: str,
        pattern: str = "*.xml",
    ) -> Iterator[dict]:
        """
        Process multiple files in a directory matching a pattern.

        Args:
            directory_path: Path to the directory to process
            pattern: Glob pattern to match files (default: *.xml)

        Yields:
            A dictionary containing the parsed data structure for each file

        Raises:
            FileNotFoundError: If the directory does not exist
            ValueError: If the path is not a directory
        """
        path = Path(directory_path)

        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")

        files = sorted(path.glob(pattern))

        if not files:
            log.warning(f"No files matching '{pattern}' found in {directory_path}")
            return

        log.debug(f"Found {len(files)} files matching '{pattern}' in {directory_path}")

        for file_path in files:
            try:
                log.debug(f"Parsing file: {file_path}")
                yield self.from_file(str(file_path))
            except Exception as e:
                log.error(f"Failed to parse {file_path}: {e}")
                continue

    def from_bytes(self, data: bytes, encoding: str = "utf-8") -> dict:
        """
        Parse binary data by decoding it to a string first.

        Args:
            data: Binary data to parse
            encoding: Character encoding to use (default: utf-8)

        Returns:
            A dictionary containing the parsed data structure

        Raises:
            ValueError: If data is empty or cannot be decoded
        """
        if not data:
            raise ValueError("Binary data is empty")

        try:
            decoded = data.decode(encoding)
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode bytes with encoding '{encoding}': {e}")

        log.debug(f"Parsing {len(data)} bytes decoded as {encoding}")
        return self.from_string(decoded)

    def from_url(self, url: str, timeout: int = 30) -> dict:
        """
        Fetch content from a URL and parse it.

        Args:
            url: URL to fetch content from
            timeout: Request timeout in seconds (default: 30)

        Returns:
            A dictionary containing the parsed data structure

        Raises:
            ImportError: If httpx is not installed
            ValueError: If the URL returns an error or empty content
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for from_url. "
                "Install it with: pip install httpx"
            )

        log.debug(f"Fetching content from URL: {url}")

        try:
            response = httpx.get(url, timeout=timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError(
                f"HTTP error fetching {url}: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            raise ValueError(f"Request error fetching {url}: {e}")

        if not response.text.strip():
            raise ValueError(f"Empty response from URL: {url}")

        log.debug(f"Fetched {len(response.text)} characters from {url}")
        return self.from_string(response.text)