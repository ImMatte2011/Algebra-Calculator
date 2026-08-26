package com.myne.alg_calc

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
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
import com.myne.alg_calc.server.PhoneHttpServer
import com.myne.alg_calc.settings.AppSettings
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException

enum class RpiStatus { UNKNOWN, CHECKING, REACHABLE, UNREACHABLE }

data class UiState(
    val bleState: BleConnectionState = BleConnectionState.Disconnected,
    val rpiStatus: RpiStatus = RpiStatus.UNKNOWN,
    val logEntries: List<LogEntry> = emptyList(),
    val espMacAddress: String = "",
    val rpiBaseUrl: String = "",
    val isConfigured: Boolean = false,
    val serverRunning: Boolean = false,
    val serverPort: Int = 8765
)

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val maxLogEntries = 200

    val settings = AppSettings(application)
    private val bleManager = BleManager(application)
    private var apiService: ApiService = buildApiService()

    private var phoneServer: PhoneHttpServer? = null
    private var serverJob: Job? = null

    private val _uiState = MutableStateFlow(
        UiState(
            espMacAddress = settings.espMacAddress,
            rpiBaseUrl    = settings.rpiBaseUrl,
            isConfigured  = settings.isConfigured(),
            serverPort    = settings.serverPort
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

    // ------------------------------------------------------------------
    // ApiService
    // ------------------------------------------------------------------

    private fun buildApiService(): ApiService {
        val url = if (AppSettings.isValidBaseUrl(settings.rpiBaseUrl)) {
            settings.rpiBaseUrl
        } else {
            "http://localhost/"
        }
        return ApiService.create(baseUrl = url, token = settings.apiToken)
    }

    // ------------------------------------------------------------------
    // BLE
    // ------------------------------------------------------------------

    fun requiredBlePermissions(): Array<String> = bleManager.requiredPermissions()

    fun connectBle() {
        addLog(LogType.INFO, "Connecting to ${settings.espMacAddress}...")
        bleManager.connect(settings.espMacAddress)
    }

    fun disconnectBle() {
        addLog(LogType.INFO, "User requested disconnect")
        bleManager.disconnect()
    }

    // ------------------------------------------------------------------
    // Settings updates
    // ------------------------------------------------------------------

    fun updateEspMac(mac: String): Boolean {
        if (!AppSettings.isValidMac(mac)) return false
        settings.espMacAddress = mac
        _uiState.value = _uiState.value.copy(
            espMacAddress = mac,
            isConfigured  = settings.isConfigured()
        )
        addLog(LogType.INFO, "ESP32 MAC updated: $mac")
        return true
    }

    fun updateRpiBaseUrl(url: String): Boolean {
        if (!AppSettings.isValidBaseUrl(url)) return false
        settings.rpiBaseUrl = url
        apiService = buildApiService()
        _uiState.value = _uiState.value.copy(
            rpiBaseUrl   = settings.rpiBaseUrl,
            rpiStatus    = RpiStatus.UNKNOWN,
            isConfigured = settings.isConfigured()
        )
        addLog(LogType.INFO, "Raspberry Pi URL updated: ${settings.rpiBaseUrl}")
        return true
    }

    fun updateApiToken(token: String) {
        settings.apiToken = token
        apiService = buildApiService()
        addLog(LogType.INFO, "API token updated")
    }

    fun updateServerPort(port: Int) {
        settings.serverPort = port
        _uiState.value = _uiState.value.copy(serverPort = port)
        if (_uiState.value.serverRunning) { stopServer(); startServer() }
    }

    fun updateEsp32Token(token: String) {
        settings.esp32Token = token
        if (_uiState.value.serverRunning) { stopServer(); startServer() }
    }

    // ------------------------------------------------------------------
    // RPi reachability check
    // ------------------------------------------------------------------

    fun testRpiConnection() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.CHECKING)
            try {
                apiService.solveExpression(MathRequest(expression = "1+1", type = "equation"))
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.REACHABLE)
                addLog(LogType.INFO, "Raspberry Pi reachable")
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.UNREACHABLE)
                addLog(LogType.ERROR, "Raspberry Pi unreachable: ${describeNetworkError(e)}")
            }
        }
    }

    // ------------------------------------------------------------------
    // ESP32 HTTP server (WiFi mode)
    // ------------------------------------------------------------------

    fun toggleServer() {
        if (_uiState.value.serverRunning) stopServer() else startServer()
    }

    fun startServer() {
        if (phoneServer?.isRunning == true) return
        val server = PhoneHttpServer(
            port       = settings.serverPort,
            esp32Token = settings.esp32Token,
            onSolve    = { expression, type, action ->
                runCatching {
                    val response = apiService.solveExpression(
                        MathRequest(expression = expression, type = type, action = action)
                    )
                    if (response.error != null) throw Exception(response.error)
                    response.result ?: throw Exception("Empty result")
                }
            }
        )
        phoneServer = server
        serverJob = viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                serverRunning = true,
                serverPort    = settings.serverPort
            )
            addLog(LogType.INFO, "ESP32 server listening on :${settings.serverPort}")
            try {
                server.start()
            } catch (e: Exception) {
                addLog(LogType.ERROR, "Server error: ${e.message}")
            } finally {
                _uiState.value = _uiState.value.copy(serverRunning = false)
            }
        }
    }

    fun stopServer() {
        phoneServer?.stop()
        serverJob?.cancel()
        phoneServer = null
        serverJob   = null
        _uiState.value = _uiState.value.copy(serverRunning = false)
        addLog(LogType.INFO, "ESP32 server stopped")
    }

    // ------------------------------------------------------------------
    // Incoming BLE packet handling (BLE mode)
    // ------------------------------------------------------------------

    private fun handleIncomingBlePacket(raw: String) {
        addLog(LogType.BLE_IN, "Received from ESP32: $raw")

        val parsed = try {
            BlePacketParser.parse(raw)
        } catch (e: BlePacketParseException) {
            addLog(LogType.ERROR, "Unparseable packet: ${e.message}")
            bleManager.sendData("err:BadFormat")
            return
        }

        addLog(
            LogType.INFO,
            "Expression: \"${parsed.expression}\" (type: ${parsed.type}" +
                "${parsed.action?.let { ", action: $it" } ?: ""})"
        )

        viewModelScope.launch {
            try {
                addLog(LogType.NET_OUT, "Sending to RPi: ${parsed.expression}")
                val response = apiService.solveExpression(
                    MathRequest(
                        expression = parsed.expression,
                        type       = parsed.type,
                        action     = parsed.action
                    )
                )
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.REACHABLE)

                if (response.error != null) {
                    addLog(LogType.ERROR, "RPi responded with error: ${response.error}")
                    bleManager.sendData("err:${response.error}")
                } else {
                    val result    = response.result ?: ""
                    val resPacket = "res:$result"
                    addLog(LogType.NET_IN,  "RPi response: $result")
                    addLog(LogType.BLE_OUT, "Send to ESP32: $resPacket")
                    bleManager.sendData(resPacket)
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(rpiStatus = RpiStatus.UNREACHABLE)
                addLog(LogType.ERROR, "Network error: ${describeNetworkError(e)}")
                bleManager.sendData("err:RPiOff")
            }
        }
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private fun describeNetworkError(e: Exception): String = when (e) {
        is SocketTimeoutException -> "timeout: the RPi did not respond in time"
        is HttpException          -> "server responded with HTTP ${e.code()}"
        is IOException            -> "RPi unreachable (network/Tailscale may be down?)"
        else                      -> e.message ?: e.toString()
    }

    private fun logForBleState(state: BleConnectionState) {
        when (state) {
            is BleConnectionState.Disconnected ->
                addLog(LogType.INFO, "BLE disconnected")
            is BleConnectionState.MissingPermissions ->
                addLog(LogType.ERROR, "Missing permissions: ${state.missing.joinToString()}")
            is BleConnectionState.Connecting ->
                addLog(LogType.INFO, "BLE connection in progress...")
            is BleConnectionState.DiscoveringServices ->
                addLog(LogType.INFO, "Discovering BLE services...")
            is BleConnectionState.Ready ->
                addLog(LogType.INFO, "BLE ready")
            is BleConnectionState.Reconnecting ->
                addLog(LogType.INFO, "Reconnecting (attempt ${state.attempt}/${state.maxAttempts})")
            is BleConnectionState.Error ->
                addLog(LogType.ERROR, "BLE error: ${state.message}")
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
        stopServer()
        bleManager.release()
    }

    companion object {
        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer {
                val application =
                    this[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY] as Application
                MainViewModel(application)
            }
        }
    }
}
