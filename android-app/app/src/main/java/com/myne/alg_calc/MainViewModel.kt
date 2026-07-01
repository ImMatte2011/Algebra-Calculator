package com.myne.alg_calc

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.myne.alg_calc.ble.BleConnectionState
import com.myne.alg_calc.ble.BleManager
import com.myne.alg_calc.ble.BlePacketParseException
import com.myne.alg_calc.ble.BlePacketParser
import com.myne.alg_calc.data.LogEntry
import com.myne.alg_calc.data.LogType
import com.myne.alg_calc.data.MathRequest
import com.myne.alg_calc.network.ApiService
import com.myne.alg_calc.settings.AppSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException

/** Stato "reachability" del Raspberry Pi, separato dallo stato BLE: sono due connessioni diverse. */
enum class RpiStatus { UNKNOWN, CHECKING, REACHABLE, UNREACHABLE }

data class UiState(
    val bleState: BleConnectionState = BleConnectionState.Disconnected,
    val rpiStatus: RpiStatus = RpiStatus.UNKNOWN,
    val logEntries: List<LogEntry> = emptyList(),
    val espMacAddress: String = "",
    val rpiBaseUrl: String = "",
    val isConfigured: Boolean = false
)

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val maxLogEntries = 200

    val settings = AppSettings(application)
    private val bleManager = BleManager(application)
    private var apiService: ApiService = buildApiService()

    private val _uiState = MutableStateFlow(
        UiState(
            espMacAddress = settings.espMacAddress,
            rpiBaseUrl = settings.rpiBaseUrl,
            isConfigured = settings.isConfigured()
        )
    )
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        bleManager.connectionState
            .onEach { state ->
                _uiState.value = _uiState.value.copy(bleState = state)
                logForBleState(state)
            }
            .launchIn(viewModelScope)

        bleManager.incomingMessages
            .onEach { raw -> handleIncomingBlePacket(raw) }
            .launchIn(viewModelScope)

        bleManager.events
            .onEach { msg -> addLog(LogType.ERROR, msg) }
            .launchIn(viewModelScope)
    }

    private fun buildApiService(): ApiService {
        // Se l'URL è vuoto o non valido, usiamo un placeholder per evitare il crash di Retrofit.
        // L'app non farà comunque chiamate finché l'utente non inserisce un URL vero.
        val url = if (AppSettings.isValidBaseUrl(settings.rpiBaseUrl)) {
            settings.rpiBaseUrl
        } else {
            "http://localhost/" // URL di sicurezza per evitare il crash
        }

        return ApiService.create(baseUrl = url, token = settings.apiToken)
    }

    fun requiredBlePermissions(): Array<String> = bleManager.requiredPermissions()

    fun connectBle() {
        addLog(LogType.INFO, "Connessione a ${settings.espMacAddress}...")
        bleManager.connect(settings.espMacAddress)
    }

    fun disconnectBle() {
        addLog(LogType.INFO, "Disconnessione richiesta dall'utente")
        bleManager.disconnect()
    }

    fun updateEspMac(mac: String): Boolean {
        if (!AppSettings.isValidMac(mac)) return false
        settings.espMacAddress = mac
        _uiState.value = _uiState.value.copy(
            espMacAddress = mac,
            isConfigured = settings.isConfigured()
        )
        addLog(LogType.INFO, "MAC ESP32 aggiornato: $mac")
        return true
    }

    fun updateRpiBaseUrl(url: String): Boolean {
        if (!AppSettings.isValidBaseUrl(url)) return false
        settings.rpiBaseUrl = url
        apiService = buildApiService()
        _uiState.value = _uiState.value.copy(
            rpiBaseUrl = settings.rpiBaseUrl,
            rpiStatus = RpiStatus.UNKNOWN,
            isConfigured = settings.isConfigured()
        )
        addLog(LogType.INFO, "URL Raspberry Pi aggiornato: ${settings.rpiBaseUrl}")
        return true
    }

    fun updateApiToken(token: String) {
        settings.apiToken = token
        apiService = buildApiService()
        addLog(LogType.INFO, "Token API aggiornato")
    }

    /** Verifica manuale di raggiungibilità del RPi, richiamabile da un pulsante in UI. */
    fun testRpiConnection() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.CHECKING)
            try {
                apiService.solveExpression(MathRequest(expression = "1+1", type = "equation"))
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.REACHABLE)
                addLog(LogType.INFO, "Raspberry Pi raggiungibile")
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.UNREACHABLE)
                addLog(LogType.ERROR, "Raspberry Pi non raggiungibile: ${describeNetworkError(e)}")
            }
        }
    }

    private fun handleIncomingBlePacket(raw: String) {
        addLog(LogType.BLE_IN, "Ricevuto da ESP32: $raw")

        val parsed = try {
            BlePacketParser.parse(raw)
        } catch (e: BlePacketParseException) {
            addLog(LogType.ERROR, "Pacchetto non interpretabile: ${e.message}")
            bleManager.sendData("err:BadFormat")
            return
        }

        addLog(LogType.INFO, "Espressione: \"${parsed.expression}\" (tipo: ${parsed.type}${parsed.action?.let { ", azione: $it" } ?: ""})")

        viewModelScope.launch {
            try {
                addLog(LogType.NET_OUT, "Invio a RPi: ${parsed.expression}")
                val response = apiService.solveExpression(
                    MathRequest(expression = parsed.expression, type = parsed.type, action = parsed.action)
                )
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.REACHABLE)

                if (response.error != null) {
                    addLog(LogType.ERROR, "RPi ha risposto con errore: ${response.error}")
                    bleManager.sendData("err:${response.error}")
                } else {
                    val result = response.result ?: ""
                    addLog(LogType.NET_IN, "Risposta RPi: $result")
                    val resPacket = "res:$result"
                    addLog(LogType.BLE_OUT, "Invio a ESP32: $resPacket")
                    bleManager.sendData(resPacket)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.UNREACHABLE)
                val description = describeNetworkError(e)
                addLog(LogType.ERROR, "Errore di rete: $description")
                bleManager.sendData("err:RPiOff")
            }
        }
    }

    private fun describeNetworkError(e: Exception): String = when (e) {
        is SocketTimeoutException -> "timeout, il RPi non ha risposto in tempo"
        is HttpException -> "il server ha risposto con HTTP ${e.code()}"
        is IOException -> "RPi irraggiungibile (rete/Tailscale non attivo?)"
        else -> e.message ?: e.toString()
    }

    private fun logForBleState(state: BleConnectionState) {
        when (state) {
            is BleConnectionState.Disconnected -> addLog(LogType.INFO, "BLE disconnesso")
            is BleConnectionState.MissingPermissions ->
                addLog(LogType.ERROR, "Permessi mancanti: ${state.missing.joinToString()}")
            is BleConnectionState.Connecting -> addLog(LogType.INFO, "Connessione BLE in corso...")
            is BleConnectionState.DiscoveringServices -> addLog(LogType.INFO, "Scoperta servizi BLE...")
            is BleConnectionState.Ready -> addLog(LogType.INFO, "BLE pronto")
            is BleConnectionState.Reconnecting ->
                addLog(LogType.INFO, "Riconnessione in corso (tentativo ${state.attempt}/${state.maxAttempts})")
            is BleConnectionState.Error -> addLog(LogType.ERROR, "Errore BLE: ${state.message}")
        }
    }

    private fun addLog(type: LogType, message: String) {
        val updated = (_uiState.value.logEntries + LogEntry(type, message)).takeLast(maxLogEntries)
        _uiState.value = _uiState.value.copy(logEntries = updated)
    }

    fun clearLog() {
        _uiState.value = _uiState.value.copy(logEntries = emptyList())
    }

    override fun onCleared() {
        super.onCleared()
        bleManager.release()
    }
    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val application = this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as Application
                MainViewModel(application)
            }
        }
    }
}