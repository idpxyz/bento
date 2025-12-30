"""
Leg Bounded Context Module.

Registers:
- Leg repositories
- Leg command/query handlers
- Leg HTTP routers
"""

from bento.runtime import BentoModule


class LegModule(BentoModule):
    """Leg bounded context module using BentoModule."""

    name = "leg"
    requires = ("infra",)

    def get_routers(self):
        """Return leg API routers."""
        from loms.contexts.leg.interfaces.http.v1.router import router

        return [router]
