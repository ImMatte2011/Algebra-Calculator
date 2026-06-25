package com.myne.alg_calc.settings

import android.content.Context

/**
 * Impostazioni dell'app persistite in SharedPreferences e modificabili dalla UI.
 *
 * I default sono stringa vuota: la prima volta che l'app viene aperta l'utente
 * deve configurare MAC, URL e token dalla schermata impostazioni.
 * Nessun valore reale è hardcoded nel sorgente.
 */
class AppSettings(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("algebric_calculator_settings", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_MAC = "esp32_mac"
        private const val KEY_BASE_URL = "rpi_base_url"
        private const val KEY_API_TOKEN = "api_token"

        // Validation in companion so they can be unit-tested without a Context
        fun isValidMac(mac: String): Boolean =
            Regex("^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$").matches(mac)

        fun isValidBaseUrl(url: String): Boolean =
            Regex("^https?://[^\\s/]+(:\\d+)?/?$").matches(url)
    }

    var espMacAddress: String
        get() = prefs.getString(KEY_MAC, "") ?: ""
        set(value) = prefs.edit().putString(KEY_MAC, value).apply()

    var rpiBaseUrl: String
        get() = prefs.getString(KEY_BASE_URL, "") ?: ""
        set(value) {
            val normalized = if (value.endsWith("/")) value else "$value/"
            prefs.edit().putString(KEY_BASE_URL, normalized).apply()
        }

    /**
     * Token Bearer per il server FastAPI.
     * Obbligatorio quando il backend gira con ACCESS_MODE=public.
     * Se vuoto, l'header Authorization non viene aggiunto (compatibile con ACCESS_MODE=tailscale).
     */
    var apiToken: String
        get() = prefs.getString(KEY_API_TOKEN, "") ?: ""
        set(value) = prefs.edit().putString(KEY_API_TOKEN, value).apply()

    /** True se le impostazioni minime per usare l'app sono state configurate. */
    fun isConfigured(): Boolean = espMacAddress.isNotBlank() && rpiBaseUrl.isNotBlank()
}