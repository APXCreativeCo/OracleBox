package com.apx.oraclebox.ui.musicbox

import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.control.ControlViewModel

class MusicBoxActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_DEVICE_ADDRESS = "device_address"
        const val EXTRA_DEVICE_NAME = "device_name"
    }

    private lateinit var viewModel: ControlViewModel

    private lateinit var buttonBackToModes: Button
    private lateinit var textMusicboxStatus: TextView
    private lateinit var textLastPlay: TextView
    private lateinit var buttonMusicboxStart: Button
    private lateinit var buttonMusicboxStop: Button
    private lateinit var buttonPlayNow: Button
    private lateinit var textCurrentMusicboxSound: TextView
    private lateinit var spinnerMusicboxSounds: Spinner
    private lateinit var buttonSetMusicboxSound: Button
    private lateinit var buttonTestMusicboxSound: Button
    private lateinit var buttonUploadMusicboxSound: Button
    private lateinit var buttonRefreshMusicboxSounds: Button
    private lateinit var progressUploadMb: ProgressBar
    private lateinit var textMusicboxLogs: TextView
    private lateinit var scrollMusicboxLogs: ScrollView

    private val pickSoundLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            val resolvedName = uri.lastPathSegment?.substringAfterLast('/')
                ?: "musicbox_${System.currentTimeMillis()}.wav"
            contentResolver.openInputStream(uri)?.use { input ->
                val data = input.readBytes()
                viewModel.uploadSound(resolvedName, data)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_musicbox)

        // Apply ghostly flicker effect to logo
        val logoImageView = findViewById<android.widget.ImageView>(R.id.image_logo_mb)
        val flickerAnim = android.view.animation.AnimationUtils.loadAnimation(this, R.anim.ghostly_flicker)
        logoImageView.startAnimation(flickerAnim)

        val deviceAddress = intent.getStringExtra(EXTRA_DEVICE_ADDRESS)
        val deviceName = intent.getStringExtra(EXTRA_DEVICE_NAME)

        val factory = ControlViewModel.Factory(application, deviceAddress)
        viewModel = ViewModelProvider(this, factory)[ControlViewModel::class.java]

        initViews()
        setupObservers()
        setupClickListeners()
        showDevelopmentNotice()
    }

    private fun showDevelopmentNotice() {
        android.app.AlertDialog.Builder(this)
            .setTitle("Development Notice")
            .setMessage("The Music Box feature is currently in development.\n\nSome features may not be fully functional yet. We're working hard to bring you the complete spirit interaction experience!")
            .setPositiveButton("Got It") { dialog, _ ->
                dialog.dismiss()
            }
            .setCancelable(false)
            .show()
    }

    private fun initViews() {
        buttonBackToModes = findViewById(R.id.button_back_to_modes_mb)
        textMusicboxStatus = findViewById(R.id.text_musicbox_status)
        textLastPlay = findViewById(R.id.text_last_play)
        buttonMusicboxStart = findViewById(R.id.button_musicbox_start)
        buttonMusicboxStop = findViewById(R.id.button_musicbox_stop)
        buttonPlayNow = findViewById(R.id.button_play_now)
        textCurrentMusicboxSound = findViewById(R.id.text_current_musicbox_sound)
        spinnerMusicboxSounds = findViewById(R.id.spinner_musicbox_sounds)
        buttonSetMusicboxSound = findViewById(R.id.button_set_musicbox_sound)
        buttonTestMusicboxSound = findViewById(R.id.button_test_musicbox_sound)
        buttonUploadMusicboxSound = findViewById(R.id.button_upload_musicbox_sound)
        buttonRefreshMusicboxSounds = findViewById(R.id.button_refresh_musicbox_sounds)
        progressUploadMb = findViewById(R.id.progress_upload_mb)
        textMusicboxLogs = findViewById(R.id.text_musicbox_logs)
        scrollMusicboxLogs = findViewById(R.id.scroll_musicbox_logs)
    }

    private fun setupObservers() {
        // Melody selection (passive buzzer melodies)
        val adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            listOf("Twinkle Star", "Lullaby", "Carousel")
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerMusicboxSounds.adapter = adapter
        
        textCurrentMusicboxSound.text = "Twinkle Star"
        progressUploadMb.visibility = android.view.View.GONE

        // Log observer for music box events
        viewModel.logs.observe(this) { logs ->
            val builder = StringBuilder()
            // Filter for Music Box related logs
            logs.takeLast(20).filter { 
                it.text.contains("MUSICBOX", ignoreCase = true) || 
                it.text.contains("MUSIC BOX", ignoreCase = true) ||
                it.text.contains("SOUND", ignoreCase = true)
            }.forEach { entry ->
                builder.append(entry.text).append("\n")
            }
            
            if (builder.isEmpty()) {
                textMusicboxLogs.text = "Waiting for activity..."
            } else {
                textMusicboxLogs.text = builder.toString()
            }
            
            // Auto-scroll to bottom
            scrollMusicboxLogs.post {
                scrollMusicboxLogs.fullScroll(ScrollView.FOCUS_DOWN)
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

        buttonMusicboxStart.setOnClickListener {
            viewModel.sendCommand("MUSICBOX START")
            textMusicboxStatus.text = "● ACTIVE"
            textMusicboxStatus.setTextColor(getColor(android.R.color.holo_green_light))
            Toast.makeText(this, "Music Box Started", Toast.LENGTH_SHORT).show()
        }

        buttonMusicboxStop.setOnClickListener {
            viewModel.sendCommand("MUSICBOX STOP")
            textMusicboxStatus.text = "● STANDBY"
            textMusicboxStatus.setTextColor(getColor(android.R.color.holo_orange_light))
            Toast.makeText(this, "Music Box Stopped", Toast.LENGTH_SHORT).show()
        }

        buttonPlayNow.setOnClickListener {
            viewModel.sendCommand("MUSICBOX PLAY")
            Toast.makeText(this, "Playing music box sound...", Toast.LENGTH_SHORT).show()
        }

        buttonSetMusicboxSound.setOnClickListener {
            val selectedMelody = spinnerMusicboxSounds.selectedItem?.toString()
            if (selectedMelody != null) {
                val melodyCode = when(selectedMelody) {
                    "Lullaby" -> "lullaby"
                    "Carousel" -> "carousel"
                    else -> "twinkle_star"
                }
                viewModel.sendCommand("MUSICBOX MELODY $melodyCode")
                textCurrentMusicboxSound.text = selectedMelody
                Toast.makeText(this, "Music Box melody set to: $selectedMelody", Toast.LENGTH_SHORT).show()
            }
        }

        buttonTestMusicboxSound.setOnClickListener {
            val selectedMelody = spinnerMusicboxSounds.selectedItem?.toString()
            if (selectedMelody != null) {
                viewModel.sendCommand("MUSICBOX PLAY")
                Toast.makeText(this, "Testing melody: $selectedMelody...", Toast.LENGTH_SHORT).show()
            }
        }

        buttonUploadMusicboxSound.setOnClickListener {
            Toast.makeText(this, "Music Box uses built-in buzzer melodies", Toast.LENGTH_SHORT).show()
        }

        buttonRefreshMusicboxSounds.setOnClickListener {
            Toast.makeText(this, "Melody list is built into firmware", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onResume() {
        super.onResume()
        // Refresh status if needed
    }
}
