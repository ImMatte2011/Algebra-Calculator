package com.myne.alg_calc.ble

/**
 * BLE connection state toward the ESP32, exposed to the UI via StateFlow.
 * Replaces the old unstructured log string: each state is typed, and the UI can
 * react (colors, badges, button enablement) without text parsing.
 */
sealed class BleConnectionState {
    /** No active connection and no attempt in progress. */
    data object Disconnected : BleConnectionState()

    /** Runtime permissions missing: the connection cannot start. */
    data class MissingPermissions(val missing: List<String>) : BleConnectionState()

    /** GATT connection attempt in progress. */
    data object Connecting : BleConnectionState()

    /** Connected at the GATT level, waiting for service/characteristic discovery. */
    data object DiscoveringServices : BleConnectionState()

    /** Ready: service found, notifications enabled, data can be sent/received. */
    data object Ready : BleConnectionState()

    /** Unexpectedly disconnected; automatic reconnect is in progress. */
    data class Reconnecting(val attempt: Int, val maxAttempts: Int) : BleConnectionState()

    /** Non-recoverable error (requires user intervention). */
    data class Error(val message: String) : BleConnectionState()
}