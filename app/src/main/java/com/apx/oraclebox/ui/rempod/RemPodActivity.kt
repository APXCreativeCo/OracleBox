package com.apx.oraclebox.ui.rempod

import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.control.ControlViewModel

class RemPodActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_DEVICE_ADDRESS = "device_address"
        const val EXTRA_DEVICE_NAME = "device_name"
    }

    private lateinit var viewModel: ControlViewModel

    private lateinit var buttonBackToModes: Button
    private lateinit var textRempodStatus: TextView
    private lateinit var textLastTrigger: TextView
    private lateinit var buttonRempodArm: Button
    private lateinit var buttonRempodDisarm: Button
    private lateinit var textCurrentRempodSound: TextView
    private lateinit var spinnerRempodSounds: Spinner
    private lateinit var buttonSetRempodSound: Button
    private lateinit var buttonTestRempodSound: Button
    private lateinit var textRempodLogs: TextView
    private lateinit var scrollRempodLogs: ScrollView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_rempod)

        val deviceAddress = intent.getStringExtra(EXTRA_DEVICE_ADDRESS)
        val deviceName = intent.getStringExtra(EXTRA_DEVICE_NAME)

        val factory = ControlViewModel.Factory(application, deviceAddress)
        viewModel = ViewModelProvider(this, factory)[ControlViewModel::class.java]

        // Apply ghostly flicker effect to logo
        val logoImageView = findViewById<android.widget.ImageView>(R.id.image_logo_rp)
        val flickerAnim = android.view.animation.AnimationUtils.loadAnimation(this, R.anim.ghostly_flicker)
        logoImageView.startAnimation(flickerAnim)

        initViews()
        setupObservers()
        setupClickListeners()
        showDevelopmentNotice()
    }

    private fun showDevelopmentNotice() {
        android.app.AlertDialog.Builder(this)
            .setTitle("Development Notice")
            .setMessage("The REM Pod feature is currently in development.\n\nSome features may not be fully functional yet. We're working hard to bring you the complete paranormal detection experience!")
            .setPositiveButton("Got It") { dialog, _ ->
                dialog.dismiss()
            }
            .setCancelable(false)
            .show()
    }

    private fun initViews() {
        buttonBackToModes = findViewById(R.id.button_back_to_modes)
        textRempodStatus = findViewById(R.id.text_rempod_status)
        textLastTrigger = findViewById(R.id.text_last_trigger)
        buttonRempodArm = findViewById(R.id.button_rempod_arm)
        buttonRempodDisarm = findViewById(R.id.button_rempod_disarm)
        textCurrentRempodSound = findViewById(R.id.text_current_rempod_sound)
        spinnerRempodSounds = findViewById(R.id.spinner_rempod_sounds)
        buttonSetRempodSound = findViewById(R.id.button_set_rempod_sound)
        buttonTestRempodSound = findViewById(R.id.button_test_rempod_sound)
        textRempodLogs = findViewById(R.id.text_rempod_logs)
        scrollRempodLogs = findViewById(R.id.scroll_rempod_logs)
    }

    private fun setupObservers() {
        // Buzzer tone selection
        val adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            listOf("Standard (2000Hz)", "High (2500Hz)", "Low (1500Hz)", "Alert (3000Hz)")
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerRempodSounds.adapter = adapter
        
        textCurrentRempodSound.text = "Standard (2000Hz)"

        // Log observer for trigger events
        viewModel.logs.observe(this) { logs ->
            val builder = StringBuilder()
            // Filter for REM Pod related logs
            logs.takeLast(20).filter { 
                it.text.contains("REMPOD", ignoreCase = true) || 
                it.text.contains("TRIGGER", ignoreCase = true)
            }.forEach { entry ->
                builder.append(entry.text).append("\n")
            }
            
            if (builder.isEmpty()) {
                textRempodLogs.text = "Waiting for triggers..."
            } else {
                textRempodLogs.text = builder.toString()
            }
            
            // Auto-scroll to bottom
            scrollRempodLogs.post {
                scrollRempodLogs.fullScroll(ScrollView.FOCUS_DOWN)
            }
        }

        // Error messages
        viewModel.errorMessage.observe(this) { msg ->
            if (!msg.isNullOrEmpty()) {
                Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun setupClickListeners() {
        buttonBackToModes.setOnClickListener {
            finish()
            overridePendingTransition(R.anim.fade_in_static, R.anim.fade_out_static)
        }

        buttonRempodArm.setOnClickListener {
            viewModel.sendCommand("REMPOD ARM")
            textRempodStatus.text = "● ARMED"
            textRempodStatus.setTextColor(getColor(android.R.color.holo_green_light))
            Toast.makeText(this, "REM Pod Armed", Toast.LENGTH_SHORT).show()
        }

        buttonRempodDisarm.setOnClickListener {
            viewModel.sendCommand("REMPOD DISARM")
            textRempodStatus.text = "● STANDBY"
            textRempodStatus.setTextColor(getColor(android.R.color.holo_orange_light))
            Toast.makeText(this, "REM Pod Disarmed", Toast.LENGTH_SHORT).show()
        }

        buttonSetRempodSound.setOnClickListener {
            val selectedTone = spinnerRempodSounds.selectedItem?.toString()
            if (selectedTone != null) {
                val frequency = when(selectedTone) {
                    "High (2500Hz)" -> 2500
                    "Low (1500Hz)" -> 1500
                    "Alert (3000Hz)" -> 3000
                    else -> 2000
                }
                viewModel.sendCommand("REMPOD TONE $frequency")
                textCurrentRempodSound.text = selectedTone
                Toast.makeText(this, "REM Pod buzzer tone set to: $selectedTone", Toast.LENGTH_SHORT).show()
            }
        }

        buttonTestRempodSound.setOnClickListener {
            val selectedTone = spinnerRempodSounds.selectedItem?.toString()
            if (selectedTone != null) {
                viewModel.sendCommand("REMPOD TEST")
                Toast.makeText(this, "Testing buzzer tone...", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Refresh status if needed
    }
}
