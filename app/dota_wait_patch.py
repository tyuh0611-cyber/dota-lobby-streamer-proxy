import time


def patch_wait_for_dota_ready_only() -> None:
    from .dota_real_adapter import RealDotaAdapter

    def _launch_gc_sync(self) -> None:
        self.gc_started = False
        self.last_gc_result = None
        self.last_gc_error = None

        if not self._dota:
            self.last_gc_error = 'dota_client_not_initialized'
            return

        try:
            result = self._dota.launch()
        except Exception as exc:
            self.last_gc_error = f'launch: {type(exc).__name__}: {exc}'
            print('DOTA_GC_LAUNCH_ERROR', self.last_gc_error, flush=True)
            return

        knock_started = False
        if not bool(getattr(self._dota, 'ready', False)):
            knock = getattr(self._dota, '_knock_on_gc', None)
            if callable(knock):
                try:
                    import gevent
                    self._dota._retry_welcome_loop = gevent.spawn(knock)
                    knock_started = True
                    print('DOTA_GC_KNOCK_LOOP_FORCED', flush=True)
                except Exception as exc:
                    print('DOTA_GC_KNOCK_LOOP_FORCE_ERROR', type(exc).__name__, exc, flush=True)

        ready_event_result = None
        ready_error = None
        ticks = 0
        deadline = time.monotonic() + 60

        while time.monotonic() < deadline:
            if bool(getattr(self._dota, 'ready', False)):
                break
            if not bool(getattr(self._client, 'logged_on', False)):
                ready_error = 'steam_disconnected_before_dota_ready'
                break

            try:
                ready_event_result = self._dota.wait_event('ready', timeout=5, raises=False)
            except TypeError:
                try:
                    ready_event_result = self._dota.wait_event('ready', timeout=5)
                except Exception as exc:
                    ready_error = f'{type(exc).__name__}: {exc}'
            except Exception as exc:
                ready_error = f'{type(exc).__name__}: {exc}'

            ticks += 1
            print(
                'DOTA_GC_WAIT_ONLY_TICK', ticks,
                'event', ready_event_result,
                'knock_started', knock_started,
                'steam_logged_on', getattr(self._client, 'logged_on', None),
                'steam_id', getattr(self._client, 'steam_id', None),
                'dota_ready', getattr(self._dota, 'ready', None),
                'dota_status', getattr(self._dota, 'connection_status', None),
                flush=True,
            )
            self._idle_dota_sync(0.5)

        dota_ready = bool(getattr(self._dota, 'ready', False))
        steam_logged_on = bool(getattr(self._client, 'logged_on', False))
        connection_status = getattr(self._dota, 'connection_status', None)

        self.gc_started = dota_ready and steam_logged_on
        self.last_gc_result = (
            f'launch: {result}; ready_event: {ready_event_result}; ticks: {ticks}; '
            f'knock_started: {knock_started}; '
            f'dota_ready: {dota_ready}; steam_logged_on: {steam_logged_on}; '
            f'connection_status: {connection_status}'
        )

        if self.gc_started:
            self.last_gc_error = None
            print('DOTA_GC_LAUNCH_OK', self.last_gc_result, flush=True)
        else:
            self.last_gc_error = ready_error or 'dota_gc_not_ready_after_launch'
            print('DOTA_GC_READY_FALSE', self.last_gc_result, self.last_gc_error, flush=True)

    RealDotaAdapter._launch_gc_sync = _launch_gc_sync
