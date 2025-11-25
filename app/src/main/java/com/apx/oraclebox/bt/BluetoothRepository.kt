package com.apx.oraclebox.bt

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.content.Context
import android.util.Log
import com.apx.oraclebox.data.LogEntry
import com.apx.oraclebox.data.OracleBoxResponse
import com.apx.oraclebox.data.OracleBoxStatus
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Repository that wraps BluetoothClient and provides higher-level OracleBox operations.
 */
class BluetoothRepository(
    private val context: Context,
    private val adapter: BluetoothAdapter
) {

    private val client = BluetoothClient(adapter)

    private val logEntries = CopyOnWriteArrayList<LogEntry>()

    fun getLogs(): List<LogEntry> = logEntries.toList()

    private fun addLog(direction: LogEntry.Direction, text: String) {
        logEntries.add(
            LogEntry(
                timestampMs = System.currentTimeMillis(),
                direction = direction,
                text = text
            )
        )
    }

    fun isConnected(): Boolean = client.isConnectedFlag

    fun getPairedDevices(): Set<BluetoothDevice> {
        return adapter.bondedDevices ?: emptySet()
    }

    @Throws(Exception::class)
    fun connectToDevice(device: BluetoothDevice) {
        client.connect(device)
        addLog(LogEntry.Direction.RECEIVED, "Connected to ${device.name} (${device.address})")
    }

    fun disconnect() {
        client.disconnect()
        addLog(LogEntry.Direction.RECEIVED, "Disconnected")
    }

    suspend fun sendRawCommand(command: String): OracleBoxResponse {
        addLog(LogEntry.Direction.SENT, command)
        return try {
            val line = client.sendCommandAndReadLine(command)
            addLog(LogEntry.Direction.RECEIVED, line)
            OracleBoxResponse(
                isOk = line.startsWith("OK"),
                raw = line
            )
        } catch (e: Exception) {
            val msg = "ERR Exception: ${e.message}"
            addLog(LogEntry.Direction.RECEIVED, msg)
            OracleBoxResponse(isOk = false, raw = msg)
        }
    }

    suspend fun requestStatus(): OracleBoxStatus? {
        val resp = sendRawCommand("STATUS")
        if (!resp.isOk) return null
        val payload = resp.raw.removePrefix("OK").trim()
        return try {
            val json = JSONObject(payload)
            OracleBoxStatus(
                speedMs = json.optInt("speed_ms", 150),
                direction = json.optString("direction", "up"),
                running = json.optBoolean("running", true),
                sweepLedMode = json.optString("sweep_led_mode", "on"),
                boxLedMode = json.optString("box_led_mode", "breath"),
                startupSound = json.optString("startup_sound", ""),
                muted = if (json.has("muted")) json.optBoolean("muted") else null
            )
        } catch (e: Exception) {
            Log.e("BluetoothRepository", "Failed to parse STATUS JSON: ${e.message}")
            null
        }
    }

    suspend fun ping(): com.apx.oraclebox.data.PingStatus? {
        val resp = sendRawCommand("PING")
        if (!resp.isOk) return null
        val payload = resp.raw.removePrefix("OK").trim()
        return try {
            val json = JSONObject(payload)
            com.apx.oraclebox.data.PingStatus(
                ok = json.optBoolean("ok", false),
                speedMs = json.optInt("speed_ms", 150),
                direction = json.optString("direction", "up"),
                running = json.optBoolean("running", true),
                sweepLedMode = json.optString("sweep_led_mode", "on"),
                boxLedMode = json.optString("box_led_mode", "breath"),
                startupSound = json.optString("startup_sound", "")
            )
        } catch (e: Exception) {
            Log.e("BluetoothRepository", "Failed to parse PING JSON: ${e.message}")
            null
        }
    }

    suspend fun setSpeed(ms: Int): OracleBoxResponse = sendRawCommand("SPEED $ms")
    suspend fun faster(): OracleBoxResponse = sendRawCommand("FASTER")
    suspend fun slower(): OracleBoxResponse = sendRawCommand("SLOWER")
    suspend fun startSweep(): OracleBoxResponse = sendRawCommand("START")
    suspend fun stopSweep(): OracleBoxResponse = sendRawCommand("STOP")
    suspend fun setDirectionUp(): OracleBoxResponse = sendRawCommand("DIR UP")
    suspend fun setDirectionDown(): OracleBoxResponse = sendRawCommand("DIR DOWN")
    suspend fun toggleDirection(): OracleBoxResponse = sendRawCommand("DIR TOGGLE")
    suspend fun setSweepLedMode(mode: String): OracleBoxResponse = sendRawCommand("LED SWEEP $mode")
    suspend fun setBoxLedMode(mode: String): OracleBoxResponse = sendRawCommand("LED BOX $mode")
    suspend fun allLedsOff(): OracleBoxResponse = sendRawCommand("LED ALL OFF")

    // NOTE: Bluetooth-based UPLOAD_SOUND is now considered legacy and the
    // Android app uses Wi‑Fi/HTTP for uploads instead. The old uploadSound
    // method has been removed in favor of HTTP handled outside this class.

    suspend fun listSounds(): List<String> {
        val resp = sendRawCommand("SOUND LIST")
        if (!resp.isOk) return emptyList()
        val prefix = "OK SOUND LIST "
        val jsonPart = resp.raw.removePrefix(prefix)
        return try {
            val arr = JSONArray(jsonPart)
            buildList {
                for (i in 0 until arr.length()) {
                    add(arr.getString(i))
                }
            }
        } catch (e: Exception) {
            Log.e("BluetoothRepository", "Failed to parse SOUND LIST JSON: ${e.message}")
            emptyList()
        }
    }

    suspend fun playSound(name: String?): OracleBoxResponse {
        return if (name.isNullOrEmpty()) {
            sendRawCommand("SOUND PLAY")
        } else {
            sendRawCommand("SOUND PLAY $name")
        }
    }

    suspend fun setStartupSound(name: String): OracleBoxResponse =
        sendRawCommand("SOUND SET $name")

    fun startListeningForLines(scope: CoroutineScope) {
        val channel = client.getReceiveChannel()
        scope.launch(Dispatchers.IO) {
            for (line in channel) {
                addLog(LogEntry.Direction.RECEIVED, line)
            }
        }
    }
}
