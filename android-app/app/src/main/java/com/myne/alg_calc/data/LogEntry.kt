package com.myne.alg_calc.data

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Sostituisce la vecchia stringa "debugLog" che cresceva all'infinito.
 * Ogni evento del bridge (ricezione BLE, invio RPi, risposta, errore...) diventa
 * una voce tipizzata, mostrabile con icona/colore diversi e con timestamp.
 */
enum class LogType {
    INFO,       // eventi generici (connessione, stato)
    BLE_IN,     // dato ricevuto dall'ESP32
    BLE_OUT,    // dato inviato all'ESP32
    NET_OUT,    // richiesta inviata al RPi
    NET_IN,     // risposta ricevuta dal RPi
    ERROR       // qualsiasi errore
}

data class LogEntry(
    val type: LogType,
    val message: String,
    val timestamp: Long = System.currentTimeMillis()
) {
    fun formattedTime(): String =
        SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(timestamp))
}