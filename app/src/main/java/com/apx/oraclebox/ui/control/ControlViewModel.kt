package com.apx.oraclebox.ui.control

import android.app.Application
import android.bluetooth.BluetoothAdapter
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.apx.oraclebox.OracleBoxApplication
import com.apx.oraclebox.bt.BluetoothRepository
import com.apx.oraclebox.data.LogEntry
import com.apx.oraclebox.data.OracleBoxStatus
import com.apx.oraclebox.data.DeviceSettingsRepository
import com.apx.oraclebox.data.PingStatus
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody

class ControlViewModel(
    application: Application,
    private val deviceAddress: String?
) : AndroidViewModel(application) {

    private val adapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
    
    // Use singleton repository to maintain connection across activities
    private val repo: BluetoothRepository? = run {
        val existing = OracleBoxApplication.getBluetoothRepository(deviceAddress)
        if (existing != null && existing.isConnected()) {
            existing
        } else {
            adapter?.let {
                val newRepo = BluetoothRepository(application.applicationContext, it)
                OracleBoxApplication.setBluetoothRepository(newRepo)
                newRepo
            }
        }
    }

    private val _status = MutableLiveData<OracleBoxStatus?>()
    val status: LiveData<OracleBoxStatus?> = _status

    private val _soundList = MutableLiveData<List<String>>(emptyList())
    val soundList: LiveData<List<String>> = _soundList

    private val _logs = MutableLiveData<List<LogEntry>>(emptyList())
    val logs: LiveData<List<LogEntry>> = _logs

    private val _uploadInProgress = MutableLiveData(false)
    val uploadInProgress: LiveData<Boolean> = _uploadInProgress

    private val _uploadProgress = MutableLiveData(0)
    val uploadProgress: LiveData<Int> = _uploadProgress

    private val _errorMessage = MutableLiveData<String?>()
    val errorMessage: LiveData<String?> = _errorMessage

    private val _disconnected = MutableLiveData(false)
    val disconnected: LiveData<Boolean> = _disconnected

    private val settingsRepo = DeviceSettingsRepository(application)

    private val _pingStatus = MutableLiveData<PingStatus?>()
    val pingStatus: LiveData<PingStatus?> = _pingStatus

    // FX State
    data class FxUiState(
        val enabled: Boolean = false,
        val preset: String = "SB7_CLASSIC",
        val bpLowHz: Int = 500,
        val bpHighHz: Int = 2600,
        val contrast: Int = 25,
        val reverbLevel: Int = 35,
        val gainDb: Int = 0,
        val loading: Boolean = false,
        val error: String? = null
    )

    private val _fxUiState = MutableLiveData(FxUiState())
    val fxUiState: LiveData<FxUiState> = _fxUiState
    
    // FX Preset State
    data class FxPreset(
        val name: String,
        val category: String,
        val description: String
    )
    
    private val _fxPresets = MutableLiveData<List<FxPreset>>(emptyList())
    val fxPresets: LiveData<List<FxPreset>> = _fxPresets

    // Mixer State
    data class MixerUiState(
        val speakerVolume: Int = 14,  // 0–37
        val micVolume: Int = 20,      // 0–35
        val autoGain: Boolean = false,
        val loading: Boolean = false,
        val error: String? = null
    )

    private val _mixerUiState = MutableLiveData(MixerUiState())
    val mixerUiState: LiveData<MixerUiState> = _mixerUiState

    init {
        connectIfNeeded()
    }

    private fun connectIfNeeded() {
        val localRepo = repo ?: return
        
        // If already connected, just update UI state and start listening
        if (localRepo.isConnected()) {
            _disconnected.postValue(false)
            localRepo.startListeningForLines(viewModelScope)
            _logs.postValue(localRepo.getLogs())
            return
        }
        
        // Not connected, so establish connection
        val addr = deviceAddress ?: return
        val adapter = BluetoothAdapter.getDefaultAdapter() ?: return
        val device = adapter.getRemoteDevice(addr)

        viewModelScope.launch(Dispatchers.IO) {
            try {
                localRepo.connectToDevice(device)
                _disconnected.postValue(false)
                localRepo.startListeningForLines(this)
            } catch (e: Exception) {
                _errorMessage.postValue("Failed to connect: ${e.message}")
                _disconnected.postValue(true)
            } finally {
                _logs.postValue(localRepo.getLogs())
            }
        }
    }

    fun refreshStatus() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            val st = withContext(Dispatchers.IO) {
                localRepo.requestStatus()
            }
            _status.value = st
            refreshLogs()
        }
    }

    fun start() = sendSimple { it.startSweep() }
    fun stop() = sendSimple { it.stopSweep() }
    fun dirUp() = sendSimple { it.setDirectionUp() }
    fun dirDown() = sendSimple { it.setDirectionDown() }
    fun dirToggle() = sendSimple { it.toggleDirection() }

    fun setSpeed(ms: Int) {
        // Optimistically update UI immediately
        val currentStatus = _status.value
        if (currentStatus != null) {
            val speedOptions = listOf(50, 100, 150, 200, 250, 300, 350)
            // Find closest valid speed
            val closestSpeed = speedOptions.minByOrNull { kotlin.math.abs(it - ms) } ?: ms
            _status.value = currentStatus.copy(speedMs = closestSpeed)
        }
        sendAndRefreshStatus { it.setSpeed(ms) }
    }

    fun faster() {
        // Optimistically update UI immediately
        val currentStatus = _status.value
        if (currentStatus != null) {
            val speedOptions = listOf(50, 100, 150, 200, 250, 300, 350)
            val currentIndex = speedOptions.indexOf(currentStatus.speedMs)
            if (currentIndex > 0) {
                val newSpeed = speedOptions[currentIndex - 1]
                _status.value = currentStatus.copy(speedMs = newSpeed)
            }
        }
        sendAndRefreshStatus { it.faster() }
    }

    fun slower() {
        // Optimistically update UI immediately
        val currentStatus = _status.value
        if (currentStatus != null) {
            val speedOptions = listOf(50, 100, 150, 200, 250, 300, 350)
            val currentIndex = speedOptions.indexOf(currentStatus.speedMs)
            if (currentIndex >= 0 && currentIndex < speedOptions.size - 1) {
                val newSpeed = speedOptions[currentIndex + 1]
                _status.value = currentStatus.copy(speedMs = newSpeed)
            }
        }
        sendAndRefreshStatus { it.slower() }
    }

    fun setSweepLedMode(mode: String) = sendAndRefreshStatus { it.setSweepLedMode(mode) }

    fun setBoxLedMode(mode: String) = sendAndRefreshStatus { it.setBoxLedMode(mode) }

    fun allLedsOff() = sendAndRefreshStatus { it.allLedsOff() }

    fun setSweepConfig(min: Int?, max: Int?, speed: Int?) {
        val localRepo = repo ?: return
        viewModelScope.launch {
            if (!localRepo.isConnected()) {
                _errorMessage.value = "Not connected to OracleBox."
                _disconnected.value = true
                return@launch
            }
            try {
                withContext(Dispatchers.IO) {
                    if (min != null) localRepo.sendRawCommand("SWEEP_CFG MIN $min")
                    if (max != null) localRepo.sendRawCommand("SWEEP_CFG MAX $max")
                    if (speed != null) localRepo.sendRawCommand("SWEEP_CFG SPEED $speed")
                }
                refreshStatus()
            } catch (e: Exception) {
                _errorMessage.value = e.message
                _disconnected.value = true
            } finally {
                refreshLogs()
            }
        }
    }

    fun setBoxConfig(min: Int?, max: Int?, speed: Int?) {
        val localRepo = repo ?: return
        viewModelScope.launch {
            if (!localRepo.isConnected()) {
                _errorMessage.value = "Not connected to OracleBox."
                _disconnected.value = true
                return@launch
            }
            try {
                withContext(Dispatchers.IO) {
                    if (min != null) localRepo.sendRawCommand("BOX_CFG MIN $min")
                    if (max != null) localRepo.sendRawCommand("BOX_CFG MAX $max")
                    if (speed != null) localRepo.sendRawCommand("BOX_CFG SPEED $speed")
                }
                refreshStatus()
            } catch (e: Exception) {
                _errorMessage.value = e.message
                _disconnected.value = true
            } finally {
                refreshLogs()
            }
        }
    }

    fun uploadSound(name: String, data: ByteArray) {
        viewModelScope.launch {
            try {
                _uploadInProgress.value = true
                _uploadProgress.value = 0
                val success = withContext(Dispatchers.IO) {
                    uploadSoundOverHttp(name, data)
                }
                if (!success) {
                    _errorMessage.value = "Upload failed over Wi‑Fi."
                } else {
                    refreshSounds()
                }
            } catch (e: Exception) {
                _errorMessage.value = e.message
            } finally {
                _uploadInProgress.value = false
                _uploadProgress.value = 0
                refreshLogs()
            }
        }
    }

    private fun uploadSoundOverHttp(name: String, data: ByteArray): Boolean {
        val baseUrl = settingsRepo.getPiBaseUrl()
        val url = "$baseUrl/upload"

        val client = OkHttpClient()

        val totalBytes = data.size.toLong()
        var lastProgress = 0

        val requestBody: RequestBody = object : RequestBody() {
            override fun contentType() = "audio/wav".toMediaTypeOrNull()

            override fun contentLength() = totalBytes

            override fun writeTo(sink: okio.BufferedSink) {
                var uploaded: Long = 0
                val bufferSize = 8 * 1024
                var offset = 0
                while (offset < data.size) {
                    val toWrite = minOf(bufferSize, data.size - offset)
                    sink.write(data, offset, toWrite)
                    offset += toWrite
                    uploaded += toWrite
                    val progress = ((uploaded * 100) / totalBytes).toInt()
                    if (progress != lastProgress) {
                        lastProgress = progress
                        _uploadProgress.postValue(progress)
                    }
                }
            }
        }

        val multipartBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", name, requestBody)
            .build()

        val request = Request.Builder()
            .url(url)
            .post(multipartBody)
            .build()

        return try {
            client.newCall(request).execute().use { resp ->
                resp.isSuccessful
            }
        } catch (e: Exception) {
            _errorMessage.postValue("HTTP upload error: ${e.message}")
            false
        }
    }

    fun refreshSounds(folder: String? = null) {
        val localRepo = repo ?: return
        viewModelScope.launch {
            val list = withContext(Dispatchers.IO) {
                localRepo.listSounds(folder)
            }
            _soundList.value = list
            refreshLogs()
        }
    }

    fun playSound(name: String?) = sendSimple { it.playSound(name) }
    fun setStartupSound(name: String) = sendSimple { it.setStartupSound(name) }

    fun sendCommand(cmd: String) {
        val localRepo = repo ?: return
        viewModelScope.launch {
            if (!localRepo.isConnected()) {
                _errorMessage.value = "Not connected to OracleBox."
                _disconnected.value = true
                return@launch
            }
            try {
                withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand(cmd)
                }
            } catch (e: Exception) {
                _errorMessage.value = e.message
                _disconnected.value = true
            } finally {
                refreshLogs()
            }
        }
    }

    fun clearStartupSound() = sendAndRefreshStatus { it.sendRawCommand("SOUND CLEAR") }

    fun getPiBaseUrl(): String = settingsRepo.getPiBaseUrl()
    fun updatePiBaseUrl(url: String) { settingsRepo.setPiBaseUrl(url) }

    fun pingPi() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                localRepo.ping()
            }
            _pingStatus.value = result
            refreshLogs()
        }
    }

    private fun sendSimple(block: suspend (BluetoothRepository) -> Unit) {
        val localRepo = repo ?: return
        viewModelScope.launch {
            if (!localRepo.isConnected()) {
                _errorMessage.value = "Not connected to OracleBox."
                _disconnected.value = true
                return@launch
            }
            try {
                withContext(Dispatchers.IO) {
                    block(localRepo)
                }
            } catch (e: Exception) {
                _errorMessage.value = e.message
                _disconnected.value = true
            } finally {
                refreshLogs()
            }
        }
    }

    private fun sendAndRefreshStatus(block: suspend (BluetoothRepository) -> Unit) {
        val localRepo = repo ?: return
        viewModelScope.launch {
            if (!localRepo.isConnected()) {
                _errorMessage.value = "Not connected to OracleBox."
                _disconnected.value = true
                return@launch
            }
            try {
                withContext(Dispatchers.IO) {
                    block(localRepo)
                    val st = localRepo.requestStatus()
                    _status.postValue(st)
                }
            } catch (e: Exception) {
                _errorMessage.value = e.message
                _disconnected.value = true
            } finally {
                refreshLogs()
            }
        }
    }

    // -------------------- FX Methods --------------------

    fun loadFxStatus() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            _fxUiState.value = _fxUiState.value?.copy(loading = true, error = null)
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.fxStatus()
                }
                if (response.isOk) {
                    val payload = response.raw.removePrefix("OK FX STATUS").trim()
                    val json = org.json.JSONObject(payload)
                    _fxUiState.value = FxUiState(
                        enabled = json.optBoolean("enabled", false),
                        preset = json.optString("preset", "SB7_CLASSIC"),
                        bpLowHz = json.optInt("bp_low", 500),
                        bpHighHz = json.optInt("bp_high", 2600),
                        contrast = json.optInt("contrast_amount", 25),
                        reverbLevel = json.optInt("reverb_room", 35),
                        gainDb = json.optInt("post_gain_db", 0),
                        loading = false,
                        error = null
                    )
                } else {
                    _fxUiState.value = _fxUiState.value?.copy(
                        loading = false,
                        error = "Failed to load FX status"
                    )
                }
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(
                    loading = false,
                    error = e.message
                )
            } finally {
                refreshLogs()
            }
        }
    }

    fun setFxEnabled(enabled: Boolean) {
        val localRepo = repo ?: return
        
        // Immediately update UI state to prevent toggle from sliding back
        _fxUiState.value = _fxUiState.value?.copy(enabled = enabled, loading = true, error = null)
        
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    if (enabled) localRepo.fxEnable() else localRepo.fxDisable()
                }
                if (response.isOk) {
                    // Refresh full status to sync all parameters
                    loadFxStatus()
                } else {
                    // Revert enabled state on failure
                    _fxUiState.value = _fxUiState.value?.copy(
                        enabled = !enabled,
                        loading = false,
                        error = "Failed to ${if (enabled) "enable" else "disable"} FX"
                    )
                }
            } catch (e: Exception) {
                // Revert enabled state on error
                _fxUiState.value = _fxUiState.value?.copy(
                    enabled = !enabled,
                    loading = false,
                    error = e.message
                )
            } finally {
                refreshLogs()
            }
        }
    }

    fun updateBandpass(lowHz: Int, highHz: Int) {
        val localRepo = repo ?: run {
            _fxUiState.value = _fxUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    localRepo.fxSet("BP_LOW", lowHz)
                    localRepo.fxSet("BP_HIGH", highHz)
                }
                _fxUiState.value = _fxUiState.value?.copy(
                    bpLowHz = lowHz,
                    bpHighHz = highHz,
                    preset = "CUSTOM",
                    error = null
                )
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(error = "BP: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    fun updateContrast(value: Int) {
        val localRepo = repo ?: run {
            _fxUiState.value = _fxUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    localRepo.fxSet("CONTRAST", value)
                }
                _fxUiState.value = _fxUiState.value?.copy(
                    contrast = value,
                    preset = "CUSTOM",
                    error = null
                )
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(error = "Contrast: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    fun updateReverb(value: Int) {
        val localRepo = repo ?: run {
            _fxUiState.value = _fxUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    localRepo.fxSet("REVERB", value)
                }
                _fxUiState.value = _fxUiState.value?.copy(
                    reverbLevel = value,
                    preset = "CUSTOM",
                    error = null
                )
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(error = "Reverb: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    fun updateGain(value: Int) {
        val localRepo = repo ?: run {
            _fxUiState.value = _fxUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    localRepo.fxSet("POST_GAIN", value)
                }
                _fxUiState.value = _fxUiState.value?.copy(
                    gainDb = value,
                    preset = "CUSTOM",
                    error = null
                )
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(error = "Gain: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    // -------------------- FX Preset Methods --------------------

    fun loadFxPresets() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.fxPresetList()
                }
                if (response.isOk) {
                    val payload = response.raw.removePrefix("OK FX PRESET LIST").trim()
                    val jsonArray = org.json.JSONArray(payload)
                    val presets = mutableListOf<FxPreset>()
                    for (i in 0 until jsonArray.length()) {
                        val obj = jsonArray.getJSONObject(i)
                        presets.add(
                            FxPreset(
                                name = obj.getString("name"),
                                category = obj.getString("category"),
                                description = obj.getString("description")
                            )
                        )
                    }
                    _fxPresets.value = presets
                }
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(error = "Failed to load presets: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    fun applyFxPreset(presetName: String) {
        val localRepo = repo ?: run {
            _fxUiState.value = _fxUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        
        // Immediately update preset name in UI for instant feedback
        _fxUiState.value = _fxUiState.value?.copy(preset = presetName, loading = true, error = null)
        
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.fxPresetSet(presetName)
                }
                if (response.isOk) {
                    // Reload FX status to get all new parameter values from backend
                    loadFxStatus()
                } else {
                    _fxUiState.value = _fxUiState.value?.copy(
                        loading = false,
                        error = "Failed to apply preset $presetName"
                    )
                }
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(
                    loading = false,
                    error = "Preset error: ${e.message}"
                )
            } finally {
                refreshLogs()
            }
        }
    }
    
    fun saveCustomPreset(presetName: String, category: String) {
        val localRepo = repo ?: run {
            _fxUiState.value = _fxUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        
        viewModelScope.launch {
            _fxUiState.value = _fxUiState.value?.copy(loading = true, error = null)
            try {
                val currentFx = _fxUiState.value ?: return@launch
                
                // Send command to save preset with current values
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand(
                        "FX PRESET SAVE $presetName $category " +
                        "${currentFx.bpLowHz} ${currentFx.bpHighHz} " +
                        "${currentFx.contrast} ${currentFx.reverbLevel} ${currentFx.gainDb}"
                    )
                }
                
                if (response.isOk) {
                    // Reload presets list to include the new one
                    loadFxPresets()
                    _fxUiState.value = _fxUiState.value?.copy(
                        preset = presetName,
                        loading = false,
                        error = null
                    )
                } else {
                    _fxUiState.value = _fxUiState.value?.copy(
                        loading = false,
                        error = "Failed to save preset"
                    )
                }
            } catch (e: Exception) {
                _fxUiState.value = _fxUiState.value?.copy(
                    loading = false,
                    error = "Save error: ${e.message}"
                )
            } finally {
                refreshLogs()
            }
        }
    }

    // -------------------- Mixer Methods --------------------

    fun loadMixerStatus() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            _mixerUiState.value = _mixerUiState.value?.copy(loading = true, error = null)
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.mixerStatus()
                }
                if (response.isOk) {
                    val payload = response.raw.removePrefix("OK MIXER STATUS").trim()
                    val json = org.json.JSONObject(payload)
                    _mixerUiState.value = MixerUiState(
                        speakerVolume = json.optInt("speaker_volume", 14),
                        micVolume = json.optInt("mic_capture_volume", 20),
                        autoGain = json.optBoolean("auto_gain", false),
                        loading = false,
                        error = null
                    )
                } else {
                    _mixerUiState.value = _mixerUiState.value?.copy(
                        loading = false,
                        error = "Failed to load mixer status"
                    )
                }
            } catch (e: Exception) {
                _mixerUiState.value = _mixerUiState.value?.copy(
                    loading = false,
                    error = e.message
                )
            } finally {
                refreshLogs()
            }
        }
    }

    fun setSpeakerVolume(level: Int) {
        val localRepo = repo ?: run {
            _mixerUiState.value = _mixerUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        val clamped = level.coerceIn(0, 37)
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.setSpeakerVolume(clamped)
                }
                if (response.isOk) {
                    _mixerUiState.value = _mixerUiState.value?.copy(speakerVolume = clamped, error = null)
                } else {
                    _mixerUiState.value = _mixerUiState.value?.copy(error = "Failed to set speaker volume")
                }
            } catch (e: Exception) {
                _mixerUiState.value = _mixerUiState.value?.copy(error = "Speaker: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    fun setMicVolume(level: Int) {
        val localRepo = repo ?: run {
            _mixerUiState.value = _mixerUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        val clamped = level.coerceIn(0, 35)
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.setMicVolume(clamped)
                }
                if (response.isOk) {
                    _mixerUiState.value = _mixerUiState.value?.copy(micVolume = clamped, error = null)
                } else {
                    _mixerUiState.value = _mixerUiState.value?.copy(error = "Failed to set mic volume")
                }
            } catch (e: Exception) {
                _mixerUiState.value = _mixerUiState.value?.copy(error = "Mic: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    fun setAutoGain(enabled: Boolean) {
        val localRepo = repo ?: run {
            _mixerUiState.value = _mixerUiState.value?.copy(error = "Bluetooth not connected")
            return
        }
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.setAutoGain(enabled)
                }
                if (response.isOk) {
                    _mixerUiState.value = _mixerUiState.value?.copy(autoGain = enabled, error = null)
                } else {
                    _mixerUiState.value = _mixerUiState.value?.copy(error = "Failed to set auto gain")
                }
            } catch (e: Exception) {
                _mixerUiState.value = _mixerUiState.value?.copy(error = "AutoGain: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }

    // ==================== BLUETOOTH AUDIO ====================
    
    private val _btAudioDevices = MutableLiveData<List<com.apx.oraclebox.data.BtAudioDevice>>(emptyList())
    val btAudioDevices: LiveData<List<com.apx.oraclebox.data.BtAudioDevice>> = _btAudioDevices
    
    private val _btAudioStatus = MutableLiveData<com.apx.oraclebox.data.BtAudioStatus?>()
    val btAudioStatus: LiveData<com.apx.oraclebox.data.BtAudioStatus?> = _btAudioStatus
    
    private val _btAudioLoading = MutableLiveData(false)
    val btAudioLoading: LiveData<Boolean> = _btAudioLoading
    
    fun refreshBtAudioDevices() {
        val localRepo = repo ?: return
        _btAudioLoading.value = true
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO LIST")
                }
                if (response.isOk) {
                    val json = org.json.JSONObject(response.raw.substringAfter("OK BT_AUDIO LIST "))
                    val devicesArray = json.optJSONArray("devices")
                    val devices = mutableListOf<com.apx.oraclebox.data.BtAudioDevice>()
                    if (devicesArray != null) {
                        for (i in 0 until devicesArray.length()) {
                            val dev = devicesArray.getJSONObject(i)
                            devices.add(
                                com.apx.oraclebox.data.BtAudioDevice(
                                    mac = dev.getString("mac"),
                                    name = dev.getString("name"),
                                    connected = dev.getBoolean("connected"),
                                    paired = true  // LIST only returns paired devices
                                )
                            )
                        }
                    }
                    _btAudioDevices.value = devices
                }
            } catch (e: Exception) {
                log("BT_AUDIO LIST error: ${e.message}")
            } finally {
                _btAudioLoading.value = false
                refreshLogs()
            }
        }
    }
    
    fun discoverBtAudioDevices() {
        val localRepo = repo ?: return
        _btAudioLoading.value = true
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO DISCOVER")
                }
                if (response.isOk) {
                    val json = org.json.JSONObject(response.raw.substringAfter("OK BT_AUDIO DISCOVER "))
                    val devicesArray = json.optJSONArray("devices")
                    val devices = mutableListOf<com.apx.oraclebox.data.BtAudioDevice>()
                    if (devicesArray != null) {
                        for (i in 0 until devicesArray.length()) {
                            val dev = devicesArray.getJSONObject(i)
                            devices.add(
                                com.apx.oraclebox.data.BtAudioDevice(
                                    mac = dev.getString("mac"),
                                    name = dev.getString("name"),
                                    connected = dev.getBoolean("connected"),
                                    paired = dev.getBoolean("paired")
                                )
                            )
                        }
                    }
                    _btAudioDevices.value = devices
                }
            } catch (e: Exception) {
                log("BT_AUDIO DISCOVER error: ${e.message}")
            } finally {
                _btAudioLoading.value = false
                refreshLogs()
            }
        }
    }
    
    fun pairAndConnectBtDevice(macAddress: String) {
        val localRepo = repo ?: return
        _btAudioLoading.value = true
        viewModelScope.launch {
            try {
                // First pair the device
                val pairResponse = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO PAIR $macAddress")
                }
                if (!pairResponse.isOk) {
                    _errorMessage.postValue("Pairing failed: ${pairResponse.raw}")
                    return@launch
                }
                
                // Then connect to it
                val connectResponse = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO CONNECT $macAddress")
                }
                if (connectResponse.isOk) {
                    refreshBtAudioStatus()
                    discoverBtAudioDevices()  // Refresh to show paired status
                } else {
                    _errorMessage.postValue("Connection failed: ${connectResponse.raw}")
                }
            } catch (e: Exception) {
                log("BT_AUDIO PAIR/CONNECT error: ${e.message}")
                _errorMessage.postValue("Error: ${e.message}")
            } finally {
                _btAudioLoading.value = false
                refreshLogs()
            }
        }
    }
    
    fun refreshBtAudioStatus() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO STATUS")
                }
                if (response.isOk) {
                    val json = org.json.JSONObject(response.raw.substringAfter("OK BT_AUDIO STATUS "))
                    _btAudioStatus.value = com.apx.oraclebox.data.BtAudioStatus(
                        defaultDevice = json.getString("default_device"),
                        btDevice = json.optString("bt_device", null),
                        btConnected = json.getBoolean("bt_connected"),
                        currentDevice = json.getString("current_device")
                    )
                }
            } catch (e: Exception) {
                log("BT_AUDIO STATUS error: ${e.message}")
            } finally {
                refreshLogs()
            }
        }
    }
    
    fun connectBtAudio(macAddress: String) {
        val localRepo = repo ?: return
        _btAudioLoading.value = true
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO CONNECT $macAddress")
                }
                if (response.isOk) {
                    refreshBtAudioStatus()
                    refreshBtAudioDevices()
                }
            } catch (e: Exception) {
                log("BT_AUDIO CONNECT error: ${e.message}")
            } finally {
                _btAudioLoading.value = false
                refreshLogs()
            }
        }
    }
    
    fun disconnectBtAudio() {
        val localRepo = repo ?: return
        _btAudioLoading.value = true
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO DISCONNECT")
                }
                if (response.isOk) {
                    refreshBtAudioStatus()
                    refreshBtAudioDevices()
                }
            } catch (e: Exception) {
                log("BT_AUDIO DISCONNECT error: ${e.message}")
            } finally {
                _btAudioLoading.value = false
                refreshLogs()
            }
        }
    }
    
    fun streamToPhone() {
        val localRepo = repo ?: return
        _btAudioLoading.value = true
        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    localRepo.sendRawCommand("BT_AUDIO STREAM_PHONE")
                }
                if (response.isOk) {
                    refreshBtAudioStatus()
                }
            } catch (e: Exception) {
                log("BT_AUDIO STREAM_PHONE error: ${e.message}")
            } finally {
                _btAudioLoading.value = false
                refreshLogs()
            }
        }
    }

    class Factory(
        private val app: Application,
        private val deviceAddress: String?
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            if (modelClass.isAssignableFrom(ControlViewModel::class.java)) {
                @Suppress("UNCHECKED_CAST")
                return ControlViewModel(app, deviceAddress) as T
            }
            throw IllegalArgumentException("Unknown ViewModel class")
        }
    }

    private fun log(message: String) {
        // Log message to repository
        val localRepo = repo ?: return
        // Repository doesn't have log method, use println for now
        println("ControlViewModel: $message")
    }

    private fun refreshLogs() {
        val localRepo = repo ?: return
        _logs.value = localRepo.getLogs()
    }
}
