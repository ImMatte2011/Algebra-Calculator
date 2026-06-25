package com.myne.alg_calc.ble

/**
 * Stato della connessione BLE verso l'ESP32, esposto alla UI tramite StateFlow.
 * Sostituisce la vecchia stringa di log non strutturata: ogni stato è tipizzato
 * e la UI può reagire (colori, badge, abilitazione pulsanti) senza fare parsing di testo.
 */
sealed class BleConnectionState {
    /** Nessuna connessione attiva, nessun tentativo in corso. */
    data object Disconnected : BleConnectionState()

    /** Permessi runtime mancanti: la connessione non può nemmeno iniziare. */
    data class MissingPermissions(val missing: List<String>) : BleConnectionState()

    /** Tentativo di connessione GATT in corso. */
    data object Connecting : BleConnectionState()

    /** Connesso a livello GATT, in attesa della scoperta dei servizi/caratteristiche. */
    data object DiscoveringServices : BleConnectionState()

    /** Tutto pronto: servizio trovato, notifiche abilitate, si possono inviare/ricevere dati. */
    data object Ready : BleConnectionState()

    /** Disconnesso in modo inatteso, tentativo di riconnessione automatica in corso. */
    data class Reconnecting(val attempt: Int, val maxAttempts: Int) : BleConnectionState()

    /** Errore non recuperabile automaticamente (serve intervento utente). */
    data class Error(val message: String) : BleConnectionState()
}