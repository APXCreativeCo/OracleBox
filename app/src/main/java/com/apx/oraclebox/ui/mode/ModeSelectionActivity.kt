package com.apx.oraclebox.ui.mode

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.control.ControlActivity
import com.apx.oraclebox.ui.control.ControlViewModel
import com.apx.oraclebox.ui.musicbox.MusicBoxActivity
import com.apx.oraclebox.ui.rempod.RemPodActivity
import com.apx.oraclebox.ui.settings.DeviceSettingsActivity

class ModeSelectionActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_DEVICE_ADDRESS = "device_address"
        const val EXTRA_DEVICE_NAME = "device_name"
        private const val PREFS_NAME = "OracleBoxPrefs"
        private const val KEY_SAVED_DEVICE_ADDRESS = "saved_device_address"
        private const val KEY_SAVED_DEVICE_NAME = "saved_device_name"
    }

    private lateinit var viewModel: ControlViewModel
    private lateinit var buttonBackToConnection: Button
    private lateinit var textConnectedDevice: TextView
    private lateinit var cardSpiritBox: LinearLayout
    private lateinit var cardRemPod: LinearLayout
    private lateinit var cardMusicBox: LinearLayout
    private lateinit var buttonDeviceSettings: Button
    private lateinit var buttonDisconnect: Button

    private var deviceAddress: String? = null
    private var deviceName: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_mode_selection)

        deviceAddress = intent.getStringExtra(EXTRA_DEVICE_ADDRESS)
        deviceName = intent.getStringExtra(EXTRA_DEVICE_NAME)

        val factory = ControlViewModel.Factory(application, deviceAddress)
        viewModel = ViewModelProvider(this, factory)[ControlViewModel::class.java]

        initViews()
        setupClickListeners()
        announceModePage()
    }

    private fun announceModePage() {
        // Play "Choose Your Investigation Method" announcement
        viewModel.playSound("choose_method.wav")
    }

    private fun initViews() {
        buttonBackToConnection = findViewById(R.id.button_back_to_connection)
        textConnectedDevice = findViewById(R.id.text_connected_device)
        cardSpiritBox = findViewById(R.id.card_spirit_box)
        cardRemPod = findViewById(R.id.card_rem_pod)
        cardMusicBox = findViewById(R.id.card_music_box)
        buttonDeviceSettings = findViewById(R.id.button_device_settings)
        buttonDisconnect = findViewById(R.id.button_disconnect)

        // Display connected device name
        textConnectedDevice.text = deviceName ?: "OracleBox"
    }

    private fun setupClickListeners() {
        buttonBackToConnection.setOnClickListener {
            finish()
            overridePendingTransition(R.anim.slide_in_left, R.anim.slide_out_right)
        }

        cardSpiritBox.setOnClickListener {
            // Announce "Spirit Box" before navigating
            viewModel.playSound("spirit_box.wav")
            val intent = Intent(this, ControlActivity::class.java).apply {
                putExtra(ControlActivity.EXTRA_DEVICE_ADDRESS, deviceAddress)
                putExtra(ControlActivity.EXTRA_DEVICE_NAME, deviceName)
            }
            startActivity(intent)
            overridePendingTransition(R.anim.fade_in_static, R.anim.fade_out_static)
        }

        cardRemPod.setOnClickListener {
            // Announce "REM Pod" before navigating
            viewModel.playSound("rempod.wav")
            val intent = Intent(this, RemPodActivity::class.java).apply {
                putExtra(RemPodActivity.EXTRA_DEVICE_ADDRESS, deviceAddress)
                putExtra(RemPodActivity.EXTRA_DEVICE_NAME, deviceName)
            }
            startActivity(intent)
            overridePendingTransition(R.anim.fade_in_static, R.anim.fade_out_static)
        }

        cardMusicBox.setOnClickListener {
            // Announce "Music Box" before navigating
            viewModel.playSound("music_box.wav")
            val intent = Intent(this, MusicBoxActivity::class.java).apply {
                putExtra(MusicBoxActivity.EXTRA_DEVICE_ADDRESS, deviceAddress)
                putExtra(MusicBoxActivity.EXTRA_DEVICE_NAME, deviceName)
            }
            startActivity(intent)
            overridePendingTransition(R.anim.fade_in_static, R.anim.fade_out_static)
        }

        buttonDeviceSettings.setOnClickListener {
            val intent = Intent(this, DeviceSettingsActivity::class.java).apply {
                putExtra(DeviceSettingsActivity.EXTRA_DEVICE_ADDRESS, deviceAddress)
                putExtra(DeviceSettingsActivity.EXTRA_DEVICE_NAME, deviceName)
            }
            startActivity(intent)
            overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
        }

        buttonDisconnect.setOnClickListener {
            // Clear saved device preference so app won't auto-connect next time
            clearSavedDevice()
            // Go back to connection screen and finish this activity
            finish()
            overridePendingTransition(R.anim.slide_in_left, R.anim.slide_out_right)
        }
    }

    override fun onBackPressed() {
        // Confirm before going back to connection screen
        super.onBackPressed()
    }

    private fun clearSavedDevice() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().apply {
            remove(KEY_SAVED_DEVICE_ADDRESS)
            remove(KEY_SAVED_DEVICE_NAME)
            apply()
        }
    }
}
