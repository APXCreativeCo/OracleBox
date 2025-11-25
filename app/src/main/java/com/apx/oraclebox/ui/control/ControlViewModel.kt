package com.apx.oraclebox.ui.control

import android.app.Application
import android.bluetooth.BluetoothAdapter
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
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
    private val repo: BluetoothRepository? = adapter?.let {
        BluetoothRepository(application.applicationContext, it)
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

    init {
        connectIfNeeded()
    }

    private fun connectIfNeeded() {
        val localRepo = repo ?: return
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

    fun setSpeed(ms: Int) = sendAndRefreshStatus { it.setSpeed(ms) }

    fun faster() = sendAndRefreshStatus { it.faster() }

    fun slower() = sendAndRefreshStatus { it.slower() }

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

    fun refreshSounds() {
        val localRepo = repo ?: return
        viewModelScope.launch {
            val list = withContext(Dispatchers.IO) {
                localRepo.listSounds()
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

    private fun refreshLogs() {
        val localRepo = repo ?: return
        _logs.value = localRepo.getLogs()
    }
}
