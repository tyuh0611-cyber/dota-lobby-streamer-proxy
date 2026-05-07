import time


def patch_real_dota_ready_check() -> None:
    from dota2.enums import EGCBaseClientMsg, EDOTAGCSessionNeed, ESourceEngine

    from .dota_real_adapter import RealDotaAdapter

    def _manual_gc_hello(self) -> None:
        self._dota.send(EGCBaseClientMsg.EMsgGCClientHello, {
            'client_session_need': EDOTAGCSessionNeed.UserInUINeverConnected,
            'engine': ESourceEngine.ESE_Source2,
        })
        print(
            'DOTA_GC_CLIENT_HELLO_SENT',
            'steam_logged_on', getattr(self._client, 'logged_on', None),
            'steam_id', getattr(self._client, 'steam_id', None),
            'dota_ready', getattr(self._dota, 'ready', None),
            'connection_status', getattr(self._dota, 'connection_status', None),
            flush=True,
        )

    def _launch_gc_sync(self) -> None:
        self.gc_started = False
        self.last_gc_result = None
        self.last_gc_error = None

        if not self._dota:
            self.last_gc_error = 'dota_client_not_initialized'
            return

        launch = getattr(self._dota, 'launch', None)
        if not callable(launch):
            self.last_gc_error = 'dota_launch_method_not_found'
            return

        try:
            result = launch()
        except Exception as exc:
            self.last_gc_error = f'launch: {type(exc).__name__}: {exc}'
            print('DOTA_GC_LAUNCH_ERROR', self.last_gc_error, flush=True)
            return

        deadline = time.monotonic() + 45
        ready_event_result = None
        ready_event_error = None
        hello_count = 0

        while time.monotonic() < deadline:
            if bool(getattr(self._dota, 'ready', False)):
                break

            steam_logged_on_now = bool(getattr(self._client, 'logged_on', False)) if self._client else False
            if not steam_logged_on_now:
                ready_event_error = 'steam_disconnected_before_dota_ready'
                break

            try:
                _manual_gc_hello(self)
                hello_count += 1
            except Exception as exc:
                ready_event_error = f'gc_hello: {type(exc).__name__}: {exc}'
                print('DOTA_GC_CLIENT_HELLO_ERROR', ready_event_error, flush=True)

            try:
                ready_event_result = self._dota.wait_event('ready', timeout=5, raises=False)
            except TypeError:
                try:
                    ready_event_result = self._dota.wait_event('ready', timeout=5)
                except Exception as exc:
                    ready_event_error = f'{type(exc).__name__}: {exc}'
            except Exception as exc:
                ready_event_error = f'{type(exc).__name__}: {exc}'

            self._idle_dota_sync(0.2)

        dota_ready = bool(getattr(self._dota, 'ready', False))
        steam_logged_on = bool(getattr(self._client, 'logged_on', False)) if self._client else False
        connection_status = getattr(self._dota, 'connection_status', None)

        self.gc_started = dota_ready and steam_logged_on
        self.last_gc_result = (
            f'launch: {result}; ready_event: {ready_event_result}; '
            f'hello_count: {hello_count}; '
            f'dota_ready: {dota_ready}; steam_logged_on: {steam_logged_on}; '
            f'connection_status: {connection_status}'
        )

        if self.gc_started:
            self.last_gc_error = None
            print('DOTA_GC_LAUNCH_OK', self.last_gc_result, flush=True)
        else:
            self.last_gc_error = ready_event_error or 'dota_gc_not_ready_after_launch'
            print('DOTA_GC_READY_FALSE', self.last_gc_result, self.last_gc_error, flush=True)

    RealDotaAdapter._launch_gc_sync = _launch_gc_sync
