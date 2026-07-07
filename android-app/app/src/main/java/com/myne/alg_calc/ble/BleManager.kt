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
 * Manages the BLE connection to the ESP32.
 *
 * Compared to the previous version:
 *  - checks runtime permissions BEFORE touching Bluetooth APIs (no more silent crashes
 *    or @SuppressLint used to hide the issue instead of fixing it);
 *  - properly closes GATT resources (no more leaks when the Activity is recreated);
 *  - attempts automatic reconnection with backoff if the disconnection was not user-initiated;
 *  - exposes state as a typed StateFlow (BleConnectionState) instead of a log string;
 *  - received messages are exposed as a SharedFlow, readable by any observer (ViewModel).
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

    /** Technical events useful for logging (e.g. write failed), separated from actual data. */
    private val _events = MutableSharedFlow<String>(extraBufferCapacity = 32)
    val events: SharedFlow<String> = _events.asSharedFlow()

    /** Required permissions, different depending on the Android version. */
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
     * Starts the connection to the specified MAC address. Should be called only after
     * runtime permissions have been verified (or requested): if missing, the state
     * switches to MissingPermissions without touching any Bluetooth API.
     */
    @SuppressLint("MissingPermission") // permissions are explicitly checked immediately below
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
                _connectionState.value = BleConnectionState.Error("Bluetooth is off or unavailable")
                return
            }
            val device = adapter.getRemoteDevice(macAddress)
            Log.d(tag, "Attempting connection to: $macAddress")
            _connectionState.value = BleConnectionState.Connecting
            bluetoothGatt = device.connectGatt(context, false, gattCallback)
        } catch (e: IllegalArgumentException) {
            _connectionState.value = BleConnectionState.Error("Invalid MAC address: $macAddress")
        }
    }

    /** User-requested disconnect: no automatic reconnection attempt. */
    @SuppressLint("MissingPermission")
    fun disconnect() {
        userInitiatedDisconnect = true
        bluetoothGatt?.disconnect()
    }

    /** Permanently closes GATT resources. Call from onDestroy/onCleared. */
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
            _connectionState.value = BleConnectionState.Error("Reconnection failed after $maxReconnectAttempts attempts")
            return
        }
        reconnectAttempt++
        _connectionState.value = BleConnectionState.Reconnecting(reconnectAttempt, maxReconnectAttempts)
        // Simple backoff: 2s, 4s, 6s, 8s, 10s
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
                    Log.d(tag, "Connected! Requesting MTU before service discovery.")
                    reconnectAttempt = 0
                    _connectionState.value = BleConnectionState.DiscoveringServices
                    // Richiedi MTU prima di discoverServices; onMtuChanged avvierà la discovery.
                    // 512 è il massimo spec BLE; il dispositivo negozierà al valore effettivo.
                    gatt.requestMtu(512)
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    Log.d(tag, "Disconnected (status=$status).")
                    gatt.close()
                    bluetoothGatt = null
                    if (userInitiatedDisconnect) {
                        _connectionState.value = BleConnectionState.Disconnected
                    } else {
                        _events.tryEmit("BLE connection unexpectedly lost (status=$status)")
                        scheduleReconnect()
                    }
                }
            }
        }

        @SuppressLint("MissingPermission")
        override fun onMtuChanged(gatt: BluetoothGatt, mtu: Int, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d(tag, "MTU negotiated: $mtu bytes (payload: ${mtu - 3} bytes)")
            } else {
                Log.w(tag, "MTU negotiation failed (status=$status), proceeding with default MTU.")
            }
            // Avvia la discovery in ogni caso: anche se la negoziazione fallisce,
            // il default (23 byte) potrebbe bastare oppure l'ESP32 potrebbe accettarlo.
            gatt.discoverServices()
        }

        @SuppressLint("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                _connectionState.value = BleConnectionState.Error("Service discovery failed (status=$status)")
                return
            }
            mainHandler.postDelayed({
                val service = gatt.getService(serviceUuid)
                if (service == null) {
                    _connectionState.value = BleConnectionState.Error("BLE service not found on ESP32")
                    return@postDelayed
                }
                val resultChar = service.getCharacteristic(resultCharUuid)
                if (resultChar == null) {
                    _connectionState.value = BleConnectionState.Error("Result characteristic not found")
                    return@postDelayed
                }

                gatt.setCharacteristicNotification(resultChar, true)
                val descriptor = resultChar.getDescriptor(clientCharacteristicConfig)
                if (descriptor == null) {
                    _connectionState.value = BleConnectionState.Error("Notification descriptor not found")
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
                Log.d(tag, "Notifications enabled successfully.")
                _connectionState.value = BleConnectionState.Ready
            } else {
                _connectionState.value = BleConnectionState.Error("Notification enable failed (status=$status)")
            }
        }

        // Called on Android 13+ (API 33+)
        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, value: ByteArray) {
            val data = String(value, Charsets.UTF_8)
            Log.d(tag, "Data received from BLE: $data")
            _incomingMessages.tryEmit(data)
        }

        // Called on Android < 13 (API < 33)
        @Suppress("DEPRECATION")
        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
                val data = String(characteristic.value ?: return, Charsets.UTF_8)
                Log.d(tag, "Data received from BLE (legacy): $data")
                _incomingMessages.tryEmit(data)
            }
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                _events.tryEmit("Data send failed (status=$status)")
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun sendData(text: String) {
        val gatt = bluetoothGatt
        val service = gatt?.getService(serviceUuid)
        val char = service?.getCharacteristic(exprCharUuid)

        if (gatt == null || char == null || _connectionState.value != BleConnectionState.Ready) {
            _events.tryEmit("Unable to send \"$text\": BLE connection not ready")
            return
        }

        Log.d(tag, "Sending to BLE: $text")
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
