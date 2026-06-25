package com.myne.alg_calc.ble

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.*
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.UUID

/**
 * Gestisce la connessione BLE verso l'ESP32.
 *
 * Rispetto alla versione precedente:
 *  - controlla i permessi runtime PRIMA di toccare le API Bluetooth (niente più crash silenziosi
 *    o @SuppressLint usato per nascondere il problema invece di risolverlo);
 *  - chiude correttamente il GATT (niente più leak quando l'Activity viene ricreata);
 *  - tenta la riconnessione automatica con backoff se la disconnessione non è richiesta dall'utente;
 *  - espone lo stato come StateFlow tipizzato (BleConnectionState) invece di una stringa di log;
 *  - i messaggi ricevuti vengono esposti come SharedFlow, leggibile da chiunque osservi (ViewModel).
 */
class BleManager(private val context: Context) {

    private val tag = "BleManager"

    private var bluetoothGatt: BluetoothGatt? = null
    private var lastMacAddress: String? = null
    private var userInitiatedDisconnect = false
    private var reconnectAttempt = 0
    private val maxReconnectAttempts = 5
    private val mainHandler = Handler(Looper.getMainLooper())

    private val serviceUuid = UUID.fromString("22337400-2cf2-4bed-8172-a832e5ba8d1f")
    private val exprCharUuid = UUID.fromString("6ee3cd41-4e4c-4bdb-809e-d45007604f4a")
    private val resultCharUuid = UUID.fromString("062251c8-1b65-47a2-83a4-4f50b781a158")
    private val clientCharacteristicConfig = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    private val _connectionState = MutableStateFlow<BleConnectionState>(BleConnectionState.Disconnected)
    val connectionState: StateFlow<BleConnectionState> = _connectionState.asStateFlow()

    private val _incomingMessages = MutableSharedFlow<String>(extraBufferCapacity = 16)
    val incomingMessages: SharedFlow<String> = _incomingMessages.asSharedFlow()

    /** Eventi "tecnici" utili per il log (es. write fallita), separati dai dati veri e propri. */
    private val _events = MutableSharedFlow<String>(extraBufferCapacity = 32)
    val events: SharedFlow<String> = _events.asSharedFlow()

    /** Permessi richiesti, diversi a seconda della versione Android. */
    fun requiredPermissions(): Array<String> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
        } else {
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    private fun missingPermissions(): List<String> {
        return requiredPermissions().filter {
            ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED
        }
    }

    fun hasAllPermissions(): Boolean = missingPermissions().isEmpty()

    /**
     * Avvia la connessione verso il MAC indicato. Va richiamata solo dopo aver verificato
     * (o richiesto) i permessi runtime: se mancano, lo stato passa a MissingPermissions
     * senza toccare nessuna API Bluetooth.
     */
    @SuppressLint("MissingPermission") // i permessi sono verificati esplicitamente subito sotto
    fun connect(macAddress: String) {
        val missing = missingPermissions()
        if (missing.isNotEmpty()) {
            _connectionState.value = BleConnectionState.MissingPermissions(missing)
            return
        }

        userInitiatedDisconnect = false
        lastMacAddress = macAddress
        reconnectAttempt = 0
        startConnection(macAddress)
    }

    @SuppressLint("MissingPermission")
    private fun startConnection(macAddress: String) {
        try {
            val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
            val adapter = bluetoothManager?.adapter
            if (adapter == null || !adapter.isEnabled) {
                _connectionState.value = BleConnectionState.Error("Bluetooth spento o non disponibile")
                return
            }
            val device = adapter.getRemoteDevice(macAddress)
            Log.d(tag, "Tentativo di connessione a: $macAddress")
            _connectionState.value = BleConnectionState.Connecting
            bluetoothGatt = device.connectGatt(context, false, gattCallback)
        } catch (e: IllegalArgumentException) {
            _connectionState.value = BleConnectionState.Error("MAC address non valido: $macAddress")
        }
    }

    /** Disconnessione voluta dall'utente: nessun tentativo di riconnessione automatica. */
    @SuppressLint("MissingPermission")
    fun disconnect() {
        userInitiatedDisconnect = true
        bluetoothGatt?.disconnect()
    }

    /** Chiude definitivamente le risorse GATT. Da chiamare in onDestroy/onCleared. */
    @SuppressLint("MissingPermission")
    fun release() {
        userInitiatedDisconnect = true
        mainHandler.removeCallbacksAndMessages(null)
        bluetoothGatt?.close()
        bluetoothGatt = null
        _connectionState.value = BleConnectionState.Disconnected
    }

    @SuppressLint("MissingPermission")
    private fun scheduleReconnect() {
        if (userInitiatedDisconnect) return
        val mac = lastMacAddress ?: return
        if (reconnectAttempt >= maxReconnectAttempts) {
            _connectionState.value = BleConnectionState.Error("Riconnessione fallita dopo $maxReconnectAttempts tentativi")
            return
        }
        reconnectAttempt++
        _connectionState.value = BleConnectionState.Reconnecting(reconnectAttempt, maxReconnectAttempts)
        // Backoff semplice: 2s, 4s, 6s, 8s, 10s
        val delayMs = 2000L * reconnectAttempt
        mainHandler.postDelayed({
            if (!userInitiatedDisconnect) {
                bluetoothGatt?.close()
                bluetoothGatt = null
                startConnection(mac)
            }
        }, delayMs)
    }

    private val gattCallback = object : BluetoothGattCallback() {

        @SuppressLint("MissingPermission")
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            when (newState) {
                BluetoothProfile.STATE_CONNECTED -> {
                    Log.d(tag, "Connesso! Avvio scoperta servizi.")
                    reconnectAttempt = 0
                    _connectionState.value = BleConnectionState.DiscoveringServices
                    gatt.discoverServices()
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.d(tag, "Disconnesso (status=$status).")
                    gatt.close()
                    bluetoothGatt = null
                    if (userInitiatedDisconnect) {
                        _connectionState.value = BleConnectionState.Disconnected
                    } else {
                        _events.tryEmit("Connessione BLE persa inaspettatamente (status=$status)")
                        scheduleReconnect()
                    }
                }
            }
        }

        @SuppressLint("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                _connectionState.value = BleConnectionState.Error("Scoperta servizi fallita (status=$status)")
                return
            }
            // Piccolo delay per stabilità dello stack BLE su alcuni dispositivi Android
            mainHandler.postDelayed({
                val service = gatt.getService(serviceUuid)
                if (service == null) {
                    _connectionState.value = BleConnectionState.Error("Servizio BLE non trovato sull'ESP32")
                    return@postDelayed
                }
                val resultChar = service.getCharacteristic(resultCharUuid)
                if (resultChar == null) {
                    _connectionState.value = BleConnectionState.Error("Caratteristica risultato non trovata")
                    return@postDelayed
                }

                gatt.setCharacteristicNotification(resultChar, true)
                val descriptor = resultChar.getDescriptor(clientCharacteristicConfig)
                if (descriptor == null) {
                    _connectionState.value = BleConnectionState.Error("Descrittore di notifica non trovato")
                    return@postDelayed
                }

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    gatt.writeDescriptor(descriptor, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
                } else {
                    @Suppress("DEPRECATION")
                    descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                    @Suppress("DEPRECATION")
                    gatt.writeDescriptor(descriptor)
                }
            }, 1000)
        }

        override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d(tag, "Notifiche abilitate correttamente.")
                _connectionState.value = BleConnectionState.Ready
            } else {
                _connectionState.value = BleConnectionState.Error("Abilitazione notifiche fallita (status=$status)")
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, value: ByteArray) {
            val data = String(value, Charsets.UTF_8)
            Log.d(tag, "Dato ricevuto dal BLE: $data")
            _incomingMessages.tryEmit(data)
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                _events.tryEmit("Invio dato fallito (status=$status)")
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun sendData(text: String) {
        val gatt = bluetoothGatt
        val service = gatt?.getService(serviceUuid)
        val char = service?.getCharacteristic(exprCharUuid)

        if (gatt == null || char == null || _connectionState.value != BleConnectionState.Ready) {
            _events.tryEmit("Impossibile inviare \"$text\": connessione BLE non pronta")
            return
        }

        Log.d(tag, "Invio al BLE: $text")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            gatt.writeCharacteristic(char, text.toByteArray(), BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT)
        } else {
            @Suppress("DEPRECATION")
            char.value = text.toByteArray()
            @Suppress("DEPRECATION")
            gatt.writeCharacteristic(char)
        }
    }
}