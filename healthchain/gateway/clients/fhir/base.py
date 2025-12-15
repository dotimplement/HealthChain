import json
import logging
import httpx

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, Optional, Type, Union
from urllib.parse import urlencode, urljoin

from fhir.resources.bundle import Bundle
from fhir.resources.capabilitystatement import CapabilityStatement
from fhir.resources.resource import Resource

from healthchain.gateway.clients.auth import OAuth2Config
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class FHIRClientError(Exception):
    """Base exception for FHIR client errors."""

    def __init__(
        self, message: str, status_code: int = None, response_data: dict = None
    ):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class FHIRAuthConfig(BaseModel):
    """Configuration for FHIR server authentication."""

    # Connection settings
    base_url: str
    timeout: int = 30
    verify_ssl: bool = True

    # OAuth2 settings (optional - for authenticated endpoints)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None  # Client secret string for standard flow
    client_secret_path: Optional[str] = (
        None  # Path to private key file for JWT assertion
    )
    token_url: Optional[str] = None
    scope: Optional[str] = "system/*.read system/*.write"
    audience: Optional[str] = None
    use_jwt_assertion: bool = False  # Use JWT client assertion (Epic/SMART style)
    key_id: Optional[str] = None  # Key ID (kid) for JWT header - required for JWKS

    @property
    def requires_auth(self) -> bool:
        """
        Auto-detect if authentication is needed based on parameters.

        Returns:
            True if any auth parameters are present, False for public endpoints
        """
        return bool(self.client_id or self.token_url)

    def model_post_init(self, __context) -> None:
        """Validate auth configuration if auth parameters are present."""
        # If no auth params, this is a public endpoint - skip validation
        if not self.requires_auth:
            return

        # If auth is required, validate configuration
        if not self.client_id:
            raise ValueError("client_id is required when using authentication")

        if not self.token_url:
            raise ValueError("token_url is required when using authentication")

        if not self.client_secret and not self.client_secret_path:
            raise ValueError(
                "Either client_secret or client_secret_path must be provided for authentication"
            )

        if self.client_secret and self.client_secret_path:
            raise ValueError("Cannot provide both client_secret and client_secret_path")

        if self.use_jwt_assertion and not self.client_secret_path:
            raise ValueError(
                "use_jwt_assertion=True requires client_secret_path to be set"
            )

        if not self.use_jwt_assertion and self.client_secret_path:
            raise ValueError(
                "client_secret_path can only be used with use_jwt_assertion=True"
            )

    def to_oauth2_config(self) -> OAuth2Config:
        """Convert to OAuth2Config for token manager."""
        return OAuth2Config(
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_secret_path=self.client_secret_path,
            token_url=self.token_url,
            scope=self.scope,
            audience=self.audience,
            use_jwt_assertion=self.use_jwt_assertion,
            key_id=self.key_id,
        )

    @classmethod
    def from_env(cls, env_prefix: str) -> "FHIRAuthConfig":
        """
        Create FHIRAuthConfig from environment variables.

        Args:
            env_prefix: Environment variable prefix (e.g., "EPIC")

        Expected environment variables:
            {env_prefix}_CLIENT_ID
            {env_prefix}_CLIENT_SECRET (or {env_prefix}_CLIENT_SECRET_PATH)
            {env_prefix}_TOKEN_URL
            {env_prefix}_BASE_URL
            {env_prefix}_SCOPE (optional)
            {env_prefix}_AUDIENCE (optional)
            {env_prefix}_TIMEOUT (optional, default: 30)
            {env_prefix}_VERIFY_SSL (optional, default: true)
            {env_prefix}_USE_JWT_ASSERTION (optional, default: false)
            {env_prefix}_KEY_ID (optional, for JWKS identification)

        Returns:
            FHIRAuthConfig instance

        Example:
            # Set environment variables:
            # EPIC_CLIENT_ID=app123
            # EPIC_CLIENT_SECRET=secret456
            # EPIC_TOKEN_URL=https://epic.com/oauth2/token
            # EPIC_BASE_URL=https://epic.com/api/FHIR/R4

            config = FHIRAuthConfig.from_env("EPIC")
        """
        import os

        # Read required environment variables
        client_id = os.getenv(f"{env_prefix}_CLIENT_ID")
        client_secret = os.getenv(f"{env_prefix}_CLIENT_SECRET")
        client_secret_path = os.getenv(f"{env_prefix}_CLIENT_SECRET_PATH")
        token_url = os.getenv(f"{env_prefix}_TOKEN_URL")
        base_url = os.getenv(f"{env_prefix}_BASE_URL")

        if not all([client_id, token_url, base_url]):
            missing = [
                var
                for var, val in [
                    (f"{env_prefix}_CLIENT_ID", client_id),
                    (f"{env_prefix}_TOKEN_URL", token_url),
                    (f"{env_prefix}_BASE_URL", base_url),
                ]
                if not val
            ]
            raise ValueError(f"Missing required environment variables: {missing}")

        # Read optional environment variables
        scope = os.getenv(f"{env_prefix}_SCOPE", "system/*.read system/*.write")
        audience = os.getenv(f"{env_prefix}_AUDIENCE")
        timeout = int(os.getenv(f"{env_prefix}_TIMEOUT", "30"))
        verify_ssl = os.getenv(f"{env_prefix}_VERIFY_SSL", "true").lower() == "true"
        use_jwt_assertion = (
            os.getenv(f"{env_prefix}_USE_JWT_ASSERTION", "false").lower() == "true"
        )
        key_id = os.getenv(f"{env_prefix}_KEY_ID")

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            client_secret_path=client_secret_path,
            token_url=token_url,
            base_url=base_url,
            scope=scope,
            audience=audience,
            timeout=timeout,
            verify_ssl=verify_ssl,
            use_jwt_assertion=use_jwt_assertion,
            key_id=key_id,
        )

    def to_connection_string(self) -> str:
        """
        Convert FHIRAuthConfig to connection string format.

        Returns:
            Connection string in fhir:// format

        Example:
            config = FHIRAuthConfig(...)
            connection_string = config.to_connection_string()
            # Returns: "fhir://hostname/path?client_id=...&token_url=..."
        """
        # Extract hostname and path from base_url
        import urllib.parse

        parsed_base = urllib.parse.urlparse(self.base_url)

        # Build query parameters
        params = {
            "client_id": self.client_id,
            "token_url": self.token_url,
        }

        # Add secret (either client_secret or client_secret_path)
        if self.client_secret:
            params["client_secret"] = self.client_secret
        elif self.client_secret_path:
            params["client_secret_path"] = self.client_secret_path

        # Add optional parameters
        if self.scope:
            params["scope"] = self.scope
        if self.audience:
            params["audience"] = self.audience
        if self.timeout != 30:
            params["timeout"] = str(self.timeout)
        if not self.verify_ssl:
            params["verify_ssl"] = "false"
        if self.use_jwt_assertion:
            params["use_jwt_assertion"] = "true"
        if self.key_id:
            params["key_id"] = self.key_id

        # Build connection string
        query_string = urllib.parse.urlencode(params)
        return f"fhir://{parsed_base.netloc}{parsed_base.path}?{query_string}"


class FHIRServerInterface(ABC):
    """
    Base FHIR client interface with common functionality.

    Provides a standardized interface for interacting with FHIR servers
    using different client libraries, with shared utility methods.
    """

    def __init__(self, auth_config: FHIRAuthConfig):
        """Initialize common client properties."""
        self.base_url = auth_config.base_url.rstrip("/") + "/"
        self.timeout = auth_config.timeout
        self.verify_ssl = auth_config.verify_ssl

        # Setup base headers
        self.base_headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }

    def _build_url(self, path: str, params: Dict[str, Any] = None) -> str:
        """Build a complete URL with optional query parameters."""
        url = urljoin(self.base_url, path)
        if params:
            # Filter out None values and convert to strings
            clean_params = {k: str(v) for k, v in params.items() if v is not None}
            if clean_params:
                url += "?" + urlencode(clean_params)
        return url

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle HTTP response and convert to dict."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise FHIRClientError(
                f"Invalid JSON response: {response.text}",
                status_code=response.status_code,
            )

        if not response.is_success:
            error_msg = f"FHIR request failed: {response.status_code}"
            if isinstance(data, dict) and "issue" in data:
                # FHIR OperationOutcome format
                issues = data.get("issue", [])
                if issues:
                    error_msg += f" - {issues[0].get('diagnostics', 'Unknown error')}"

            raise FHIRClientError(
                error_msg, status_code=response.status_code, response_data=data
            )

        return data

    @lru_cache(maxsize=128)
    def _resolve_resource_type(
        self, resource_type: Union[str, Type[Resource]]
    ) -> tuple[str, Type[Resource]]:
        """
        Resolve FHIR resource type to string name and class. Cached with LRU.

        Args:
            resource_type: FHIR resource type or class

        Returns:
            Tuple of (type_name: str, resource_class: Type[Resource])
        """
        if hasattr(resource_type, "__name__"):
            # It's already a class
            type_name = resource_type.__name__
            resource_class = resource_type
        else:
            # It's a string, need to dynamically import
            type_name = str(resource_type)
            module_name = f"fhir.resources.{type_name.lower()}"
            module = __import__(module_name, fromlist=[type_name])
            resource_class = getattr(module, type_name)

        return type_name, resource_class

    @abstractmethod
    def read(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> Resource:
        """Read a specific resource by ID."""
        pass

    @abstractmethod
    def create(self, resource: Resource) -> Resource:
        """Create a new resource."""
        pass

    @abstractmethod
    def update(self, resource: Resource) -> Resource:
        """Update an existing resource."""
        pass

    @abstractmethod
    def delete(
        self, resource_type: Union[str, Type[Resource]], resource_id: str
    ) -> bool:
        """Delete a resource."""
        pass

    @abstractmethod
    def search(
        self,
        resource_type: Union[str, Type[Resource]],
        params: Optional[Dict[str, Any]] = None,
    ) -> Bundle:
        """Search for resources."""
        pass

    @abstractmethod
    def transaction(self, bundle: Bundle) -> Bundle:
        """Execute a transaction bundle."""
        pass

    @abstractmethod
    def capabilities(self) -> CapabilityStatement:
        """Get the capabilities of the FHIR server."""
        pass


def parse_fhir_auth_connection_string(connection_string: str) -> FHIRAuthConfig:
    """
    Parse a FHIR connection string into authentication configuration.

    Supports both authenticated and unauthenticated (public) endpoints:
    - Authenticated: fhir://hostname/path?client_id=xxx&client_secret=xxx&token_url=xxx
    - Public: fhir://hostname/path (no auth parameters)

    Args:
        connection_string: FHIR connection string with optional OAuth2 credentials

    Returns:
        FHIRAuthConfig with parsed settings

    Raises:
        ValueError: If connection string is invalid

    Examples:
        # Authenticated endpoint
        config = parse_fhir_auth_connection_string(
            "fhir://epic.com/api/FHIR/R4?client_id=app&client_secret=secret&token_url=https://epic.com/token"
        )

        # Public endpoint (no auth)
        config = parse_fhir_auth_connection_string(
            "fhir://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
        )
    """
    import urllib.parse

    if not connection_string.startswith("fhir://"):
        raise ValueError("Connection string must start with fhir://")

    parsed = urllib.parse.urlparse(connection_string)
    params = dict(urllib.parse.parse_qsl(parsed.query))

    # Build base URL
    base_url = f"https://{parsed.netloc}{parsed.path}"

    # Auto-detect if auth is needed based on parameter presence
    has_client_id = "client_id" in params
    has_token_url = "token_url" in params
    has_secret = "client_secret" in params
    has_secret_path = "client_secret_path" in params

    # If no auth params at all, this is a public endpoint
    if not any([has_client_id, has_token_url, has_secret, has_secret_path]):
        return FHIRAuthConfig(
            base_url=base_url,
            timeout=int(params.get("timeout", 30)),
            verify_ssl=params.get("verify_ssl", "true").lower() == "true",
        )

    # If any auth param is present, validate complete auth config
    # FHIRAuthConfig.model_post_init will handle validation
    return FHIRAuthConfig(
        client_id=params.get("client_id"),
        client_secret=params.get("client_secret"),
        client_secret_path=params.get("client_secret_path"),
        token_url=params.get("token_url"),
        scope=params.get("scope", "system/*.read system/*.write"),
        audience=params.get("audience"),
        base_url=base_url,
        timeout=int(params.get("timeout", 30)),
        verify_ssl=params.get("verify_ssl", "true").lower() == "true",
        use_jwt_assertion=params.get("use_jwt_assertion", "false").lower() == "true",
        key_id=params.get("key_id"),
    )
