package com.myne.alg_calc

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberMultiplePermissionsState
import com.myne.alg_calc.ble.BleConnectionState
import com.myne.alg_calc.data.LogEntry
import com.myne.alg_calc.data.LogType
import com.myne.alg_calc.ui.theme.AlgebricCalculatorTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AlgebricCalculatorTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    BridgeScreen()
                }
            }
        }
    }
}

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun BridgeScreen(viewModel: MainViewModel = viewModel(factory = MainViewModel.Factory)) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val permissionsState = rememberMultiplePermissionsState(
        permissions = viewModel.requiredBlePermissions().toList()
    )
    var showSettings by remember { mutableStateOf(false) }
    var autoConnectAttempted by remember { mutableStateOf(false) }

    LaunchedEffect(permissionsState.allPermissionsGranted) {
        if (permissionsState.allPermissionsGranted && !autoConnectAttempted) {
            autoConnectAttempted = true
            viewModel.connectBle()
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            "Bridge BLE \u2194 RPi",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(12.dp))

        if (!permissionsState.allPermissionsGranted) {
            PermissionRequestCard(onRequestClick = { permissionsState.launchMultiplePermissionRequest() })
            Spacer(modifier = Modifier.height(12.dp))
        }

        StatusRow(uiState = uiState)
        Spacer(modifier = Modifier.height(12.dp))

        ActionRow(
            bleState           = uiState.bleState,
            permissionsGranted = permissionsState.allPermissionsGranted,
            serverRunning      = uiState.serverRunning,
            serverPort         = uiState.serverPort,
            onConnect          = { viewModel.connectBle() },
            onDisconnect       = { viewModel.disconnectBle() },
            onTestRpi          = { viewModel.testRpiConnection() },
            onToggleServer     = { viewModel.toggleServer() },
            onSettings         = { showSettings = true },
            onClearLog         = { viewModel.clearLog() }
        )
        Spacer(modifier = Modifier.height(12.dp))

        Text("Event log", style = MaterialTheme.typography.titleSmall)
        Spacer(modifier = Modifier.height(4.dp))
        LogList(entries = uiState.logEntries, modifier = Modifier.weight(1f))
    }

    if (showSettings) {
        SettingsDialog(
            initialMac         = uiState.espMacAddress,
            initialUrl         = uiState.rpiBaseUrl,
            initialServerPort  = uiState.serverPort.toString(),
            initialEsp32Token  = viewModel.settings.esp32Token,
            onDismiss          = { showSettings = false },
            onSave             = { mac, url, portStr, token ->
                val macOk  = viewModel.updateEspMac(mac)
                val urlOk  = viewModel.updateRpiBaseUrl(url)
                val port   = portStr.toIntOrNull()
                if (port != null) viewModel.updateServerPort(port)
                viewModel.updateEsp32Token(token)
                macOk && urlOk && port != null
            }
        )
    }
}

@Composable
private fun PermissionRequestCard(onRequestClick: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "Bluetooth permissions required",
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onErrorContainer
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                "The app cannot connect to the ESP32 without the Bluetooth/location permissions requested by the system.",
                color = MaterialTheme.colorScheme.onErrorContainer
            )
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = onRequestClick) { Text("Grant permissions") }
        }
    }
}

@Composable
private fun StatusRow(uiState: UiState) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        StatusBadge(
            label    = "ESP32",
            text     = bleStateLabel(uiState.bleState),
            color    = bleStateColor(uiState.bleState),
            modifier = Modifier.weight(1f)
        )
        StatusBadge(
            label    = "Raspberry Pi",
            text     = rpiStatusLabel(uiState.rpiStatus),
            color    = rpiStatusColor(uiState.rpiStatus),
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun StatusBadge(label: String, text: String, color: Color, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(color.copy(alpha = 0.15f))
            .padding(12.dp)
    ) {
        Text(label, style = MaterialTheme.typography.labelMedium)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(RoundedCornerShape(50))
                    .background(color)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(text, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ActionRow(
    bleState: BleConnectionState,
    permissionsGranted: Boolean,
    serverRunning: Boolean,
    serverPort: Int,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit,
    onTestRpi: () -> Unit,
    onToggleServer: () -> Unit,
    onSettings: () -> Unit,
    onClearLog: () -> Unit
) {
    val isConnectedOrConnecting = bleState !is BleConnectionState.Disconnected &&
        bleState !is BleConnectionState.Error &&
        bleState !is BleConnectionState.MissingPermissions

    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        if (isConnectedOrConnecting) {
            OutlinedButton(onClick = onDisconnect, modifier = Modifier.weight(1f)) {
                Text("Disconnect")
            }
        } else {
            Button(onClick = onConnect, enabled = permissionsGranted, modifier = Modifier.weight(1f)) {
                Text("Connect BLE")
            }
        }
        OutlinedButton(onClick = onTestRpi, modifier = Modifier.weight(1f)) {
            Text("Test RPi")
        }
    }

    Spacer(modifier = Modifier.height(8.dp))

    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Button(
            onClick = onToggleServer,
            colors  = ButtonDefaults.buttonColors(
                containerColor = if (serverRunning) MaterialTheme.colorScheme.error
                else MaterialTheme.colorScheme.secondary
            ),
            modifier = Modifier.weight(1f)
        ) {
            Text(if (serverRunning) "Stop server :$serverPort" else "Start ESP32 server")
        }
        TextButton(onClick = onSettings, modifier = Modifier.weight(1f)) {
            Text("Settings")
        }
    }

    Spacer(modifier = Modifier.height(4.dp))

    TextButton(
        onClick  = onClearLog,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text("Clear log")
    }
}

@Composable
private fun LogList(entries: List<LogEntry>, modifier: Modifier = Modifier) {
    val listState = rememberLazyListState()
    val scope     = rememberCoroutineScope()

    LaunchedEffect(entries.size) {
        if (entries.isNotEmpty()) {
            scope.launch { listState.animateScrollToItem(entries.size - 1) }
        }
    }

    Card(modifier = modifier.fillMaxWidth()) {
        if (entries.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize().padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                Text("No events yet", style = MaterialTheme.typography.bodySmall)
            }
        } else {
            LazyColumn(state = listState, modifier = Modifier.padding(8.dp)) {
                items(entries) { entry -> LogRow(entry) }
            }
        }
    }
}

@Composable
private fun LogRow(entry: LogEntry) {
    val (icon, color) = when (entry.type) {
        LogType.INFO    -> "\u2139\uFE0F" to MaterialTheme.colorScheme.onSurfaceVariant
        LogType.BLE_IN  -> "\uD83D\uDCE5" to MaterialTheme.colorScheme.primary
        LogType.BLE_OUT -> "\uD83D\uDCE4" to MaterialTheme.colorScheme.primary
        LogType.NET_OUT -> "\uD83D\uDCE1" to MaterialTheme.colorScheme.tertiary
        LogType.NET_IN  -> "\uD83D\uDCF6" to MaterialTheme.colorScheme.tertiary
        LogType.ERROR   -> "\u274C"        to MaterialTheme.colorScheme.error
    }
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text(icon, modifier = Modifier.padding(end = 6.dp))
        Column {
            Text(
                entry.formattedTime(),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(entry.message, style = MaterialTheme.typography.bodySmall, color = color)
        }
    }
}

@Composable
private fun SettingsDialog(
    initialMac: String,
    initialUrl: String,
    initialServerPort: String,
    initialEsp32Token: String,
    onDismiss: () -> Unit,
    onSave: (mac: String, url: String, serverPort: String, esp32Token: String) -> Boolean
) {
    var mac         by remember { mutableStateOf(initialMac) }
    var url         by remember { mutableStateOf(initialUrl) }
    var serverPort  by remember { mutableStateOf(initialServerPort) }
    var esp32Token  by remember { mutableStateOf(initialEsp32Token) }
    var error       by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Settings") },
        text  = {
            Column {
                OutlinedTextField(
                    value         = mac,
                    onValueChange = { mac = it },
                    label         = { Text("ESP32 MAC (XX:XX:XX:XX:XX:XX)") },
                    singleLine    = true,
                    modifier      = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value         = url,
                    onValueChange = { url = it },
                    label         = { Text("Raspberry Pi URL (http://IP:PORT/)") },
                    singleLine    = true,
                    modifier      = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value         = serverPort,
                    onValueChange = { serverPort = it },
                    label         = { Text("ESP32 server port (default 8765)") },
                    singleLine    = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier      = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value         = esp32Token,
                    onValueChange = { esp32Token = it },
                    label         = { Text("ESP32 shared token (empty = no auth)") },
                    singleLine    = true,
                    modifier      = Modifier.fillMaxWidth()
                )
                error?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        it,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val ok = onSave(mac.trim(), url.trim(), serverPort.trim(), esp32Token.trim())
                if (ok) onDismiss()
                else error = "Invalid values — check MAC, URL and port"
            }) { Text("Save") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

// ------------------------------------------------------------------
// Label / color helpers
// ------------------------------------------------------------------

private fun bleStateLabel(state: BleConnectionState): String = when (state) {
    is BleConnectionState.Disconnected       -> "Disconnected"
    is BleConnectionState.MissingPermissions -> "Missing permissions"
    is BleConnectionState.Connecting         -> "Connecting..."
    is BleConnectionState.DiscoveringServices -> "Discovering services..."
    is BleConnectionState.Ready              -> "Connected"
    is BleConnectionState.Reconnecting       -> "Reconnecting ${state.attempt}/${state.maxAttempts}"
    is BleConnectionState.Error              -> "Error"
}

@Composable
private fun bleStateColor(state: BleConnectionState): Color = when (state) {
    is BleConnectionState.Ready              -> Color(0xFF2E7D32)
    is BleConnectionState.Connecting,
    is BleConnectionState.DiscoveringServices,
    is BleConnectionState.Reconnecting       -> Color(0xFFF9A825)
    is BleConnectionState.Disconnected       -> MaterialTheme.colorScheme.onSurfaceVariant
    is BleConnectionState.MissingPermissions,
    is BleConnectionState.Error              -> MaterialTheme.colorScheme.error
}

private fun rpiStatusLabel(status: RpiStatus): String = when (status) {
    RpiStatus.UNKNOWN     -> "Unknown"
    RpiStatus.CHECKING    -> "Checking..."
    RpiStatus.REACHABLE   -> "Reachable"
    RpiStatus.UNREACHABLE -> "Unreachable"
}

@Composable
private fun rpiStatusColor(status: RpiStatus): Color = when (status) {
    RpiStatus.REACHABLE   -> Color(0xFF2E7D32)
    RpiStatus.CHECKING    -> Color(0xFFF9A825)
    RpiStatus.UNKNOWN     -> MaterialTheme.colorScheme.onSurfaceVariant
    RpiStatus.UNREACHABLE -> MaterialTheme.colorScheme.error
}
