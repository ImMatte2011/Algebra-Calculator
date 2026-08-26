package com.myne.alg_calc.settings

import android.content.Context

/**
 * App settings persisted in SharedPreferences and editable from the UI.
 *
 * Defaults are empty strings: when the app is first opened the user must
 * configure MAC, URL, and token from the settings screen.
 * No real value is hardcoded in source.
 */
class AppSettings(context: Context) {

    private val prefs = context.applicationContext
        .getSharedPreferences("algebric_calculator_settings", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_MAC = "esp32_mac"
        private const val KEY_BASE_URL = "rpi_base_url"
        private const val KEY_API_TOKEN = "api_token"
        private const val KEY_SERVER_ENABLED = "server_enabled"
        private const val KEY_SERVER_PORT    = "server_port"
        private const val KEY_ESP32_TOKEN    = "esp32_token"

        // Validation in companion so they can be unit-tested without a Context
        fun isValidMac(mac: String): Boolean =
            Regex("^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$").matches(mac)

        fun isValidBaseUrl(url: String): Boolean {
            if (url.isBlank()) return false
            return Regex("^https?://[^\\s/]+(:\\d+)?/?$").matches(url)
        }
    }

    var serverEnabled: Boolean
        get() = prefs.getBoolean(KEY_SERVER_ENABLED, false)
        set(v) = prefs.edit().putBoolean(KEY_SERVER_ENABLED, v).apply()

    var serverPort: Int
        get() = prefs.getInt(KEY_SERVER_PORT, 8765)
        set(v) = prefs.edit().putInt(KEY_SERVER_PORT, v).apply()

    /** Shared secret: must match PHONE_TOKEN in ESP32 config.py. Empty = no auth. */
    var esp32Token: String
        get() = prefs.getString(KEY_ESP32_TOKEN, "") ?: ""
        set(v) = prefs.edit().putString(KEY_ESP32_TOKEN, v).apply()

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
     * Bearer token for the FastAPI server.
     * Required when the backend runs with ACCESS_MODE=public.
     * When empty, the Authorization header is not added (compatible with ACCESS_MODE=tailscale).
     */
    var apiToken: String
        get() = prefs.getString(KEY_API_TOKEN, "") ?: ""
        set(value) = prefs.edit().putString(KEY_API_TOKEN, value).apply()

    /** True if the minimal settings required to use the app are configured. */
    fun isConfigured(): Boolean = espMacAddress.isNotBlank() && rpiBaseUrl.isNotBlank()
}
