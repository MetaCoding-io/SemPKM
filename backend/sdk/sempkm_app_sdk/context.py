"""AppContext — runtime context with scoped HTTP clients and template rendering.

Created by the runner from CLI args and passed to the App's ASGI builder.
Provides lazy-init client stubs that share a single platform HTTP client.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from sempkm_app_sdk.clients.commands import CommandClient
    from sempkm_app_sdk.clients.graph import GraphClient
    from sempkm_app_sdk.clients.http import HttpClient
    from sempkm_app_sdk.clients.settings import SettingsClient
    from sempkm_app_sdk.clients.state import StateClient

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Runtime context provided to app handlers and client stubs.

    Attributes:
        app_id: Unique application identifier.
        app_dir: Path to the app's installation directory.
        platform_url: Base URL of the SemPKM platform API.
        app_token: Shared secret token for platform↔app authentication.
        permissions: Manifest permissions dict. Expected shape::

            {
                "commands": ["object.create", "body.set"],
                "sparql_read": True,
                "network": {"domains": ["*.example.com"]},
            }
    """

    app_id: str
    app_dir: Path
    platform_url: str
    app_token: str
    permissions: dict = field(default_factory=dict)

    # Private lazy-init storage
    _platform_client: httpx.AsyncClient | None = field(
        default=None, init=False, repr=False
    )
    _jinja_env: Environment | None = field(
        default=None, init=False, repr=False
    )
    _commands_client: CommandClient | None = field(
        default=None, init=False, repr=False
    )
    _graph_client: GraphClient | None = field(
        default=None, init=False, repr=False
    )
    _state_client: StateClient | None = field(
        default=None, init=False, repr=False
    )
    _http_client: HttpClient | None = field(
        default=None, init=False, repr=False
    )
    _settings_client: SettingsClient | None = field(
        default=None, init=False, repr=False
    )

    @property
    def iri_prefix(self) -> str:
        """IRI prefix for this app: ``urn:sempkm:app:{app_id}:``."""
        return f"urn:sempkm:app:{self.app_id}:"

    def _get_platform_client(self) -> httpx.AsyncClient:
        """Return the shared platform HTTP client, creating it lazily."""
        if self._platform_client is None:
            self._platform_client = httpx.AsyncClient(
                base_url=self.platform_url,
                headers={"Authorization": f"Bearer {self.app_token}"},
            )
            logger.debug(
                "platform HTTP client created for %s → %s",
                self.app_id,
                self.platform_url,
            )
        return self._platform_client

    @property
    def commands(self) -> CommandClient:
        """Command execution client with permission enforcement."""
        if self._commands_client is None:
            from sempkm_app_sdk.clients.commands import CommandClient

            allowed = set(self.permissions.get("commands", []))
            self._commands_client = CommandClient(
                self._get_platform_client(),
                allowed_commands=allowed,
                iri_prefix=self.iri_prefix,
            )
        return self._commands_client

    @property
    def graph(self) -> GraphClient:
        """SPARQL graph query client with read permission gate."""
        if self._graph_client is None:
            from sempkm_app_sdk.clients.graph import GraphClient

            self._graph_client = GraphClient(
                self._get_platform_client(),
                sparql_read=bool(self.permissions.get("sparql_read", False)),
            )
        return self._graph_client

    @property
    def state(self) -> StateClient:
        """App state (key-value) client scoped to app's named graph."""
        if self._state_client is None:
            from sempkm_app_sdk.clients.state import StateClient

            self._state_client = StateClient(
                self._get_platform_client(), self.app_id
            )
        return self._state_client

    @property
    def http(self) -> HttpClient:
        """External HTTP client with domain enforcement."""
        if self._http_client is None:
            from sempkm_app_sdk.clients.http import HttpClient

            network = self.permissions.get("network", {})
            domains = network.get("domains", []) if isinstance(network, dict) else network
            self._http_client = HttpClient(allowed_domains=domains)
        return self._http_client

    @property
    def settings(self) -> SettingsClient:
        """App settings client stub (delegates to state)."""
        if self._settings_client is None:
            from sempkm_app_sdk.clients.settings import SettingsClient

            self._settings_client = SettingsClient(self.state)
        return self._settings_client

    def render_template(self, template_name: str, **context: object) -> str:
        """Render a Jinja2 template from the app's frontend/templates dir.

        Args:
            template_name: Template filename relative to
                ``{app_dir}/frontend/templates/``.
            **context: Template context variables.

        Returns:
            Rendered template string.
        """
        if self._jinja_env is None:
            template_dir = self.app_dir / "frontend" / "templates"
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=True,
            )
            logger.debug("jinja2 env created for %s", template_dir)
        template = self._jinja_env.get_template(template_name)
        return template.render(**context)

    async def close(self) -> None:
        """Close the shared platform HTTP client and external HTTP client."""
        if self._platform_client is not None:
            await self._platform_client.aclose()
            self._platform_client = None
            logger.debug("platform HTTP client closed for %s", self.app_id)
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None
