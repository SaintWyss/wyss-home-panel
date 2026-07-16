from wyss_panel_bridge.domain.models import FastCommand, PolicyError

ALLOWED_ACTIONS = frozenset({"turn_on", "turn_off", "toggle", "set_brightness", "activate_scene"})


def validate_fast_command(command: FastCommand, allowed_entities: frozenset[str]) -> None:
    if command.entity_id not in allowed_entities:
        raise PolicyError("La entidad no está autorizada para este panel")
    if command.action not in ALLOWED_ACTIONS:
        raise PolicyError("La acción no pertenece al camino rápido")
    if command.action == "set_brightness" and not (
        command.brightness is not None and 0 <= command.brightness <= 100
    ):
        raise PolicyError("El brillo debe estar entre 0 y 100")
