package com.apx.oraclebox.data

/**
 * Kotlin model for OracleBox STATUS JSON.
 */
data class OracleBoxStatus(
    val speedMs: Int,
    val direction: String,
    val running: Boolean,
    val sweepLedMode: String,
    val boxLedMode: String,
    val startupSound: String
    ,
    val muted: Boolean? = false
)

/**
 * Generic response wrapper from OracleBox.
 * Every line is either:
 *   "OK something..." or "ERR something..."
 */
data class OracleBoxResponse(
    val isOk: Boolean,
    val raw: String
)

/**
 * Simple log entry for the UI.
 */
data class LogEntry(
    val timestampMs: Long,
    val direction: Direction,
    val text: String
) {
    enum class Direction { SENT, RECEIVED }
}

/**
 * Diagnostic payload returned by PING.
 */
data class PingStatus(
    val ok: Boolean,
    val speedMs: Int,
    val direction: String,
    val running: Boolean,
    val sweepLedMode: String,
    val boxLedMode: String,
    val startupSound: String
    ,
    val muted: Boolean? = false
)

/**
 * Bluetooth audio device info.
 */
data class BtAudioDevice(
    val mac: String,
    val name: String,
    val connected: Boolean,
    val paired: Boolean = true  // Default true for backward compatibility with LIST command
)

/**
 * Bluetooth audio status from BT_AUDIO STATUS command.
 */
data class BtAudioStatus(
    val defaultDevice: String,
    val btDevice: String?,
    val btConnected: Boolean,
    val currentDevice: String
)
