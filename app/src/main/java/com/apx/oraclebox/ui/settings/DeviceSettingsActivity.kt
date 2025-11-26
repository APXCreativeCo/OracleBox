package com.apx.oraclebox.ui.settings

import android.os.Bundle
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.control.ControlActivity
import com.apx.oraclebox.ui.control.ControlViewModel

class DeviceSettingsActivity : AppCompatActivity() {

    private lateinit var viewModel: ControlViewModel

    private val pickSoundLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            val resolvedName = uri.lastPathSegment?.substringAfterLast('/')
                ?: "startup_${System.currentTimeMillis()}.wav"
            contentResolver.openInputStream(uri)?.use { input ->
                val data = input.readBytes()
                viewModel.uploadSound(resolvedName, data)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_device_settings)

        val deviceAddress = intent.getStringExtra(ControlActivity.EXTRA_DEVICE_ADDRESS)
        val deviceName = intent.getStringExtra(ControlActivity.EXTRA_DEVICE_NAME)

        val factory = ControlViewModel.Factory(application, deviceAddress)
        viewModel = ViewModelProvider(this, factory)[ControlViewModel::class.java]

        val buttonBackToModes: Button = findViewById(R.id.button_back_to_modes_ds)
        val textDeviceName: TextView = findViewById(R.id.text_device_name)
        val textDeviceAddr: TextView = findViewById(R.id.text_device_addr)
        val editPiBaseUrl: EditText = findViewById(R.id.edit_pi_base_url)
        val buttonSaveBaseUrl: Button = findViewById(R.id.button_save_base_url)
        val textStartupSound: TextView = findViewById(R.id.text_startup_sound_settings)
        val buttonUploadSound: Button = findViewById(R.id.button_upload_sound_settings)
        val buttonPlaySound: Button = findViewById(R.id.button_play_sound_settings)
        val buttonRefreshSounds: Button = findViewById(R.id.button_refresh_sounds_settings)
        val spinnerSounds: Spinner = findViewById(R.id.spinner_sounds_settings)
        val buttonSetStartup: Button = findViewById(R.id.button_set_startup_settings)
        val buttonClearStartup: Button = findViewById(R.id.button_clear_startup)
        val progressUpload: ProgressBar = findViewById(R.id.progress_upload_settings)
        val buttonPing: Button = findViewById(R.id.button_ping)
        val textPingResult: TextView = findViewById(R.id.text_ping_result)
        val buttonRefreshBtDevices: Button = findViewById(R.id.button_refresh_bt_devices)
        val textBtAudioStatus: TextView = findViewById(R.id.text_bt_audio_status)
        val textBtDeviceList: TextView = findViewById(R.id.text_bt_device_list)
        val buttonDisconnectBt: Button = findViewById(R.id.button_disconnect_bt)
        val buttonStreamToPhone: Button = findViewById(R.id.button_stream_to_phone)

        buttonBackToModes.setOnClickListener {
            finish()
            overridePendingTransition(R.anim.slide_in_left, R.anim.slide_out_right)
        }

        textDeviceName.text = deviceName ?: "Unknown"
        textDeviceAddr.text = deviceAddress ?: "Unknown"
        editPiBaseUrl.setText(viewModel.getPiBaseUrl())

        buttonSaveBaseUrl.setOnClickListener {
            val v = editPiBaseUrl.text?.toString()?.trim().orEmpty()
            if (v.isEmpty()) {
                Toast.makeText(this, "Base URL cannot be empty", Toast.LENGTH_SHORT).show()
            } else {
                viewModel.updatePiBaseUrl(v)
                Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show()
            }
        }

        viewModel.status.observe(this) { st ->
            textStartupSound.text = if (st?.startupSound.isNullOrBlank()) "None" else st?.startupSound
        }

        viewModel.soundFiles.observe(this) { sounds ->
            val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item,
                sounds.map { it.name })
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            spinnerSounds.adapter = adapter
        }

        viewModel.uploadProgress.observe(this) { progress ->
            if (progress == null) {
                progressUpload.visibility = android.view.View.GONE
            } else {
                progressUpload.visibility = android.view.View.VISIBLE
                progressUpload.progress = progress
            }
        }

        buttonUploadSound.setOnClickListener {
            pickSoundLauncher.launch("audio/*")
        }

        buttonPlaySound.setOnClickListener {
            val pos = spinnerSounds.selectedItemPosition
            val sounds = viewModel.soundFiles.value ?: return@setOnClickListener
            if (pos >= 0 && pos < sounds.size) {
                viewModel.playSound(sounds[pos].name)
            }
        }

        buttonRefreshSounds.setOnClickListener {
            viewModel.refreshSoundFiles()
        }

        buttonSetStartup.setOnClickListener {
            val pos = spinnerSounds.selectedItemPosition
            val sounds = viewModel.soundFiles.value ?: return@setOnClickListener
            if (pos >= 0 && pos < sounds.size) {
                viewModel.setStartupSound(sounds[pos].name)
                viewModel.refreshStatus()
            }
        }

        viewModel.pingStatus.observe(this) { ps ->
            if (ps == null) {
                textPingResult.text = "Ping failed"
            } else {
                val lines = listOf(
                    "ok=${ps.ok}",
                    "running=${ps.running}",
                    "dir=${ps.direction}",
                    "speedMs=${ps.speedMs}",
                    "sweepLed=${ps.sweepLedMode}",
                    "boxLed=${ps.boxLedMode}",
                    "startup=${if (ps.startupSound.isBlank()) "None" else ps.startupSound}"
                )
                textPingResult.text = lines.joinToString("\n")
            }
        }

        buttonClearStartup.setOnClickListener {
            viewModel.clearStartupSound()
            viewModel.refreshStatus()
        }

        buttonPing.setOnClickListener {
            viewModel.pingPi()
        }

        buttonRefreshBtDevices.setOnClickListener {
            viewModel.refreshBtAudioDevices()
            viewModel.refreshBtAudioStatus()
        }

        buttonDisconnectBt.setOnClickListener {
            viewModel.disconnectBtAudio()
        }

        buttonStreamToPhone.setOnClickListener {
            viewModel.streamToPhone()
            Toast.makeText(this, "Routing audio to this phone...", Toast.LENGTH_SHORT).show()
        }

        // Observe Bluetooth audio status
        viewModel.btAudioStatus.observe(this) { status ->
            if (status == null) {
                textBtAudioStatus.text = "No Bluetooth audio info"
            } else {
                val lines = listOf(
                    "Output: ${status.currentDevice}",
                    "BT Connected: ${status.btConnected}",
                    if (status.btDevice != null) "BT Device: ${status.btDevice}" else "BT Device: None"
                )
                textBtAudioStatus.text = lines.joinToString("\n")
            }
        }

        // Observe Bluetooth device list
        viewModel.btAudioDevices.observe(this) { devices ->
            if (devices.isEmpty()) {
                textBtDeviceList.text = "No Bluetooth audio devices found"
            } else {
                val lines = devices.map { dev ->
                    "${dev.name}\n${dev.mac}\n${if (dev.connected) "✓ Connected" else "⊗ Not connected"}"
                }
                textBtDeviceList.text = lines.joinToString("\n\n")
                
                // Make device list clickable
                textBtDeviceList.setOnClickListener {
                    showBtDeviceSelectionDialog(devices)
                }
            }
        }

        // Load initial status for display
        viewModel.refreshStatus()
        viewModel.refreshBtAudioStatus()
        viewModel.refreshSoundFiles()
    }

    private fun showBtDeviceSelectionDialog(devices: List<com.apx.oraclebox.data.BtAudioDevice>) {
        val deviceNames = devices.map { "${it.name} (${it.mac})" }.toTypedArray()
        
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Connect Bluetooth Headphones")
            .setItems(deviceNames) { _, which ->
                val selectedDevice = devices[which]
                viewModel.connectBtAudio(selectedDevice.mac)
                Toast.makeText(this, "Connecting to ${selectedDevice.name}...", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}
