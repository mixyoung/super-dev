"""Compatibility mixin that combines the host-operation modules."""

from __future__ import annotations

from .cli_host_commands_mixin import CliHostCommandsMixin
from .cli_host_discovery_mixin import CliHostDiscoveryMixin
from .cli_host_guidance_mixin import CliHostGuidanceMixin


class CliHostOpsMixin(
    CliHostDiscoveryMixin,
    CliHostCommandsMixin,
    CliHostGuidanceMixin,
):
    """Keep the established public mixin while splitting its responsibilities."""
