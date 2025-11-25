package com.apx.oraclebox.ui.connection

import android.app.Application
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.apx.oraclebox.bt.BluetoothRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ConnectionViewModel(application: Application) : AndroidViewModel(application) {

    private val adapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
    private val repo: BluetoothRepository? = adapter?.let {
        BluetoothRepository(application.applicationContext, it)
    }

    private val _pairedDevices = MutableLiveData<List<BluetoothDevice>>(emptyList())
    val pairedDevices: LiveData<List<BluetoothDevice>> = _pairedDevices

    private val _connectionStatus = MutableLiveData("Not connected")
    val connectionStatus: LiveData<String> = _connectionStatus

    private val _isConnecting = MutableLiveData(false)
    val isConnecting: LiveData<Boolean> = _isConnecting

    private val _navigateToControl = MutableLiveData(false)
    val navigateToControl: LiveData<Boolean> = _navigateToControl

    private val _errorMessage = MutableLiveData<String?>()
    val errorMessage: LiveData<String?> = _errorMessage

    fun refreshPairedDevices() {
        val bt = adapter ?: run {
            _errorMessage.value = "Bluetooth not supported on this device."
            return
        }
        _pairedDevices.value = bt.bondedDevices?.toList() ?: emptyList()
    }

    fun connectTo(device: BluetoothDevice) {
        val localRepo = repo ?: run {
            _errorMessage.value = "Bluetooth not supported."
            return
        }

        _isConnecting.value = true
        _errorMessage.value = null
        _connectionStatus.value = "Connecting to ${device.name}..."

        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) {
                try {
                    localRepo.connectToDevice(device)
                    true
                } catch (e: Exception) {
                    _errorMessage.postValue("Failed to connect: ${e.message}")
                    false
                }
            }
            _isConnecting.value = false
            if (result) {
                _connectionStatus.value = "Connected to ${device.name}"
                _navigateToControl.value = true
            } else {
                _connectionStatus.value = "Not connected"
            }
        }
    }

    fun onNavigatedToControl() {
        _navigateToControl.value = false
    }
}
