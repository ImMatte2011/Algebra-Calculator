package com.myne.alg_calc.server

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.ServerSocket
import java.net.Socket

/**
 * Minimal HTTP server that listens for POST /solve requests from the ESP32.
 * Validates a Bearer token to accept only the configured ESP32.
 * Forwards the request to the RPi via [onSolve] and returns the result.
 */
class PhoneHttpServer(
    val port: Int = 8765,
    private val esp32Token: String,
    private val onSolve: suspend (expression: String, type: String, action: String?) -> Result<String>
) {
    private var serverSocket: ServerSocket? = null

    @Volatile
    var isRunning = false
        private set

    suspend fun start() = withContext(Dispatchers.IO) {
        serverSocket = ServerSocket(port)
        isRunning = true
        while (isRunning) {
            try {
                val client = serverSocket!!.accept()
                handleClient(client)
            } catch (_: Exception) { /* socket closed or transient error */ }
        }
    }

    fun stop() {
        isRunning = false
        try { serverSocket?.close() } catch (_: Exception) {}
        serverSocket = null
    }

    private suspend fun handleClient(socket: Socket) = withContext(Dispatchers.IO) {
        try {
            val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
            val writer = PrintWriter(socket.getOutputStream(), true)

            // Request line (e.g. "POST /solve HTTP/1.0")
            val requestLine = reader.readLine() ?: return@withContext

            // Headers
            val headers = mutableMapOf<String, String>()
            var contentLength = 0
            var line = reader.readLine()
            while (!line.isNullOrBlank()) {
                val idx = line.indexOf(':')
                if (idx > 0) {
                    val key   = line.substring(0, idx).trim().lowercase()
                    val value = line.substring(idx + 1).trim()
                    headers[key] = value
                    if (key == "content-length") contentLength = value.toIntOrNull() ?: 0
                }
                line = reader.readLine()
            }

            // Token validation — skip if token not configured
            if (esp32Token.isNotBlank()) {
                val auth = headers["authorization"] ?: ""
                if (auth != "Bearer $esp32Token") {
                    respond(writer, 401, """{"ok":false,"error":"Unauthorized"}""")
                    return@withContext
                }
            }

            // Body
            val bodyChars = CharArray(contentLength)
            reader.read(bodyChars, 0, contentLength)
            val json = JSONObject(String(bodyChars))

            val expression = json.optString("expression")
            val type       = json.optString("type")
            val action     = if (json.isNull("action")) null else json.optString("action").ifBlank { null }

            if (expression.isBlank() || type.isBlank()) {
                respond(writer, 400, """{"ok":false,"error":"Missing fields"}""")
                return@withContext
            }

            val result = onSolve(expression, type, action)
            result.fold(
                onSuccess = { respond(writer, 200, """{"ok":true,"result":"$it"}""") },
                onFailure = { respond(writer, 400, """{"ok":false,"error":"${it.message}"}""") }
            )
        } catch (_: Exception) {
        } finally {
            socket.close()
        }
    }

    private fun respond(writer: PrintWriter, status: Int, body: String) {
        val statusText = when (status) { 200 -> "OK"; 401 -> "Unauthorized"; else -> "Bad Request" }
        writer.print("HTTP/1.0 $status $statusText\r\n")
        writer.print("Content-Type: application/json\r\n")
        writer.print("Content-Length: ${body.length}\r\n")
        writer.print("Connection: close\r\n\r\n")
        writer.print(body)
        writer.flush()
    }
}
