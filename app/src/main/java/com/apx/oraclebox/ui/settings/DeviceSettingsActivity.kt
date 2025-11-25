package com.apx.oraclebox.ui.settings

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.control.ControlActivity
import com.apx.oraclebox.ui.control.ControlViewModel

class DeviceSettingsActivity : AppCompatActivity() {

    private lateinit var viewModel: ControlViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_device_settings)

        val deviceAddress = intent.getStringExtra(ControlActivity.EXTRA_DEVICE_ADDRESS)
        val deviceName = intent.getStringExtra(ControlActivity.EXTRA_DEVICE_NAME)

        val factory = ControlViewModel.Factory(application, deviceAddress)
        viewModel = ViewModelProvider(this, factory)[ControlViewModel::class.java]

        val textDeviceName: TextView = findViewById(R.id.text_device_name)
        val textDeviceAddr: TextView = findViewById(R.id.text_device_addr)
        val editPiBaseUrl: EditText = findViewById(R.id.edit_pi_base_url)
        val buttonSaveBaseUrl: Button = findViewById(R.id.button_save_base_url)
        val textStartupSound: TextView = findViewById(R.id.text_startup_sound_settings)
        val buttonClearStartup: Button = findViewById(R.id.button_clear_startup)
        val buttonPing: Button = findViewById(R.id.button_ping)
        val textPingResult: TextView = findViewById(R.id.text_ping_result)

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

        // Load initial status for display
        viewModel.refreshStatus()
    }
}
