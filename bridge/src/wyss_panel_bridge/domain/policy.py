from wyss_panel_bridge.domain.models import FastCommand, PolicyError

ALLOWED_ACTIONS = frozenset(
    {"turn_on", "turn_off", "toggle", "set_brightness", "set_color", "activate_scene"}
)


def validate_fast_command(command: FastCommand, allowed_entities: frozenset[str]) -> None:
    if command.entity_id not in allowed_entities:
        raise PolicyError("La entidad no está autorizada para este panel")
    if command.action not in ALLOWED_ACTIONS:
        raise PolicyError("La acción no pertenece al camino rápido")
    is_scene = command.entity_id.startswith("scene.")
    if command.action == "activate_scene":
        if not is_scene or command.brightness is not None or command.rgb is not None:
            raise PolicyError("La escena o sus parámetros no son válidos")
        return
    if is_scene:
        raise PolicyError("Una escena sólo admite activación")
    if not command.entity_id.startswith("light."):
        raise PolicyError("El camino rápido sólo controla luces o escenas")
    if command.action == "set_brightness":
        if command.brightness is None or not 0 <= command.brightness <= 100:
            raise PolicyError("El brillo debe estar entre 0 y 100")
        if command.rgb is not None:
            raise PolicyError("El brillo no admite color simultáneo")
        return
    if command.action == "set_color":
        if command.rgb is None or not 0 <= command.rgb <= 0xFFFFFF:
            raise PolicyError("El color RGB debe estar entre 000000 y FFFFFF")
        if command.brightness is not None:
            raise PolicyError("El color no admite brillo simultáneo")
        return
    if command.brightness is not None or command.rgb is not None:
        raise PolicyError("La acción no admite parámetros de brillo o color")
