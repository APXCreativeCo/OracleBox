package com.apx.oraclebox.bt

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.io.PrintWriter
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Classic Bluetooth SPP client for OracleBox.
 *
 * Responsibilities:
 *  - Hold the RFCOMM socket.
 *  - Connect to a selected BluetoothDevice via SPP UUID.
 *  - Provide a suspend sendCommandAndReadLine() that writes "CMD\n" and reads a single line.
 */
class BluetoothClient(
    private val adapter: BluetoothAdapter
) {

    companion object {
        // We connect directly to RFCOMM channel 1 (no SDP),
        // since some OracleBox setups cannot advertise an SPP UUID.
        private const val RFCOMM_CHANNEL = 1
        private const val TAG = "BluetoothClient"
    }

    private var socket: BluetoothSocket? = null
    private var writer: PrintWriter? = null
    private var reader: BufferedReader? = null

    private val receiveChannel = Channel<String>(Channel.BUFFERED)
    private val isConnected = AtomicBoolean(false)
    private var ioJob: Job? = null

    val isConnectedFlag: Boolean
        get() = isConnected.get()

    /**
     * Connects to the given device using a direct RFCOMM socket on channel 1.
     * This avoids relying on SDP / SPP UUID, which may not be available
     * on some OracleBox Pi images.
     * Must be called off the main thread.
     */
    @Throws(Exception::class)
    fun connect(device: BluetoothDevice) {
        disconnect()

        // Use hidden createRfcommSocket(int channel) via reflection to
        // open a classic RFCOMM socket directly on channel 1.
        val method = device.javaClass.getMethod("createRfcommSocket", Int::class.javaPrimitiveType)
        val tmpSocket = method.invoke(device, RFCOMM_CHANNEL) as BluetoothSocket
        adapter.cancelDiscovery()

        tmpSocket.connect() // blocking connect

        socket = tmpSocket
        writer = PrintWriter(OutputStreamWriter(tmpSocket.outputStream), true)
        reader = BufferedReader(InputStreamReader(tmpSocket.inputStream))

        isConnected.set(true)

        // Background loop to read lines for logging or future streaming.
        ioJob = CoroutineScope(Dispatchers.IO).launch {
            try {
                while (isActive && isConnected.get()) {
                    val line = reader?.readLine() ?: break
                    receiveChannel.send(line)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Receive loop error: ${e.message}", e)
            } finally {
                isConnected.set(false)
            }
        }
    }

    fun disconnect() {
        isConnected.set(false)
        ioJob?.cancel()
        ioJob = null

        try {
            reader?.close()
        } catch (_: Exception) {
        }
        try {
            writer?.close()
        } catch (_: Exception) {
        }
        try {
            socket?.close()
        } catch (_: Exception) {
        }

        reader = null
        writer = null
        socket = null
    }

    /**
     * Sends a single command and waits for ONE line response.
     * Command SHOULD NOT include "\n"; this function appends it.
     */
    suspend fun sendCommandAndReadLine(command: String): String {
        if (!isConnected.get()) {
            throw IllegalStateException("Not connected")
        }

        return withContext(Dispatchers.IO) {
            writer?.let {
                it.print(command)
                it.print("\n")
                it.flush()
            } ?: throw IllegalStateException("Writer is null")

            val line = reader?.readLine()
                ?: throw IllegalStateException("Connection closed while reading")

            line
        }
    }

    /**
     * Reads a single line from the connection without sending anything.
     * Useful for multi-step protocols like file upload.
     */
    suspend fun readLine(): String {
        if (!isConnected.get()) {
            throw IllegalStateException("Not connected")
        }

        return withContext(Dispatchers.IO) {
            val line = reader?.readLine()
                ?: throw IllegalStateException("Connection closed while reading")
            line
        }
    }

    /**
     * Writes raw bytes to the socket without adding newlines.
     */
    suspend fun writeBytes(bytes: ByteArray) {
        if (!isConnected.get()) {
            throw IllegalStateException("Not connected")
        }

        withContext(Dispatchers.IO) {
            val out = socket?.outputStream ?: throw IllegalStateException("Output stream is null")
            out.write(bytes)
            out.flush()
        }
    }

    fun getReceiveChannel(): Channel<String> = receiveChannel
}
