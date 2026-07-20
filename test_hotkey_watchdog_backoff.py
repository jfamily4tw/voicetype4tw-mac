from hotkey.listener import HotkeyListener


def test_watchdog_retries_initial_burst_then_low_frequency():
    listener = HotkeyListener(
        hotkey_configs={},
        on_start=lambda mode: None,
        on_stop=lambda mode: None,
    )

    attempts = [i for i in range(1, 25) if listener._should_retry_disabled_tap(i)]

    assert attempts == [1, 2, 3, 12, 24]
