package com.myne.alg_calc.data

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Replaces the old "debugLog" string that used to grow without bounds.
 * Each bridge event (BLE receive, RPi send, response, error, etc.) becomes
 * a typed entry that can be displayed with different icon/color and timestamp.
 */
enum class LogType {
    INFO,       // generic events (connection, state)
    BLE_IN,     // data received from the ESP32
    BLE_OUT,    // data sent to the ESP32
    NET_OUT,    // request sent to the RPi
    NET_IN,     // response received from the RPi
    ERROR       // any error
}

data class LogEntry(
    val type: LogType,
    val message: String,
    val timestamp: Long = System.currentTimeMillis()
) {
    fun formattedTime(): String =
        SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(timestamp))
}