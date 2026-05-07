import time
from typing import Any


def _summarize_message(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value

    data = {'type': type(value).__name__, 'text': str(value)[:2000]}
    for field_name in ('result', 'lobby_id', 'leader_id', 'status'):
        if hasattr(value, field_name):
            data[field_name] = str(getattr(value, field_name))
    return data


def patch_real_dota_adapter_create_lobby() -> None:
    from dota2.enums import EDOTAGCMsg

    from .dota_real_adapter import RealDotaAdapter

    def _create_lobby_sync(self, pw: str, options: dict) -> dict:
        result = self._dota.create_practice_lobby(pw, options)

        practice_response = None
        try:
            practice_response = self._dota.wait_msg(
                EDOTAGCMsg.EMsgGCPracticeLobbyResponse,
                timeout=8,
                raises=False,
            )
        except TypeError:
            try:
                practice_response = self._dota.wait_msg(
                    EDOTAGCMsg.EMsgGCPracticeLobbyResponse,
                    timeout=8,
                )
            except Exception as exc:
                practice_response = f'{type(exc).__name__}: {exc}'
        except Exception as exc:
            practice_response = f'{type(exc).__name__}: {exc}'

        events = []
        deadline = time.monotonic() + 35

        while time.monotonic() < deadline:
            lobby = getattr(self._dota, 'lobby', None)
            if lobby is not None:
                break

            for event_name in ('lobby_new', 'lobby_changed'):
                if getattr(self._dota, 'lobby', None) is not None:
                    break

                try:
                    event_result = self._dota.wait_event(event_name, timeout=2, raises=False)
                    events.append({event_name: str(event_result)})
                except TypeError:
                    event_result = self._dota.wait_event(event_name, timeout=2)
                    events.append({event_name: str(event_result)})
                except Exception as exc:
                    events.append({event_name: f'{type(exc).__name__}: {exc}'})

            self._idle_dota_sync(0.25)

        lobby = getattr(self._dota, 'lobby', None)

        return {
            'create_result': str(result),
            'practice_response': _summarize_message(practice_response),
            'events': events[-12:],
            'lobby_detected': lobby is not None,
            'lobby_id': str(getattr(lobby, 'lobby_id', '')) if lobby else None,
            'leader_id': str(getattr(lobby, 'leader_id', '')) if lobby else None,
        }

    RealDotaAdapter._create_lobby_sync = _create_lobby_sync
