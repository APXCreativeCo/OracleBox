package com.apx.oraclebox.ui.control

import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.data.LogEntry

class ControlActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_DEVICE_ADDRESS = "device_address"
        const val EXTRA_DEVICE_NAME = "device_name"
    }

    private lateinit var viewModel: ControlViewModel

    private lateinit var textRunning: TextView
    private lateinit var textDirection: TextView
    private lateinit var textSpeed: TextView
    private lateinit var textSweepLed: TextView
    private lateinit var textBoxLed: TextView

    private lateinit var buttonStart: Button
    private lateinit var buttonStop: Button
    private lateinit var buttonDirUp: Button
    private lateinit var buttonDirDown: Button
    private lateinit var buttonMute: Button

    private lateinit var spinnerSpeed: Spinner
    private lateinit var buttonFaster: Button
    private lateinit var buttonSlower: Button

    private lateinit var spinnerSweepLed: Spinner
    private lateinit var spinnerBoxLed: Spinner

    private lateinit var buttonRefreshStatus: Button
    private lateinit var buttonRefreshSounds: Button
    private lateinit var buttonUploadSound: Button
    private lateinit var spinnerSounds: Spinner
    private lateinit var buttonPlaySound: Button
    private lateinit var buttonSetStartup: Button
    private lateinit var buttonSetRempod: Button
    private lateinit var buttonSetMusicbox: Button
    private lateinit var buttonDeviceSettings: Button

    private lateinit var seekSweepMin: SeekBar
    private lateinit var seekSweepMax: SeekBar
    private lateinit var seekSweepSpeed: SeekBar
    private lateinit var seekBoxMin: SeekBar
    private lateinit var seekBoxMax: SeekBar
    private lateinit var seekBoxSpeed: SeekBar
    private lateinit var buttonApplySweepCfg: Button
    private lateinit var buttonApplyBoxCfg: Button

    private lateinit var textLogs: TextView
    private lateinit var labelDisconnected: TextView
    private lateinit var progressUpload: ProgressBar

    private val speedOptions = listOf(50, 100, 150, 200, 250, 300, 350)
    private val ledModes = listOf(
        "on",
        "off",
        "breath",
        "breath_fast",
        "heartbeat",
        "strobe",
        "flicker",
        "random_burst",
        "sweep"
    )

    private var isMuted: Boolean = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_control)

        val deviceAddress = intent.getStringExtra(EXTRA_DEVICE_ADDRESS)
        val factory = ControlViewModel.Factory(application, deviceAddress)
        viewModel = ViewModelProvider(this, factory)[ControlViewModel::class.java]

        bindViews()
        setupSpinners()
        setupObservers()
        setupButtons()

        viewModel.refreshStatus()
    }

    private fun bindViews() {
        textRunning = findViewById(R.id.text_running)
        textDirection = findViewById(R.id.text_direction)
        textSpeed = findViewById(R.id.text_speed)
        textSweepLed = findViewById(R.id.text_sweep_led)
        textBoxLed = findViewById(R.id.text_box_led)

        buttonStart = findViewById(R.id.button_start)
        buttonStop = findViewById(R.id.button_stop)
        buttonDirUp = findViewById(R.id.button_dir_up)
        buttonDirDown = findViewById(R.id.button_dir_down)
        buttonMute = findViewById(R.id.button_mute)

        spinnerSpeed = findViewById(R.id.spinner_speed)
        buttonFaster = findViewById(R.id.button_faster)
        buttonSlower = findViewById(R.id.button_slower)

        spinnerSweepLed = findViewById(R.id.spinner_sweep_led)
        spinnerBoxLed = findViewById(R.id.spinner_box_led)

        buttonRefreshStatus = findViewById(R.id.button_refresh_status)
        buttonRefreshSounds = findViewById(R.id.button_refresh_sounds)
        buttonUploadSound = findViewById(R.id.button_upload_sound)
        spinnerSounds = findViewById(R.id.spinner_sounds)
        buttonPlaySound = findViewById(R.id.button_play_sound)
        buttonSetStartup = findViewById(R.id.button_set_startup)

        buttonSetRempod = findViewById(R.id.button_set_rempod)
        buttonSetMusicbox = findViewById(R.id.button_set_musicbox)
        buttonDeviceSettings = findViewById(R.id.button_device_settings)

        seekSweepMin = findViewById(R.id.seek_sweep_min)
        seekSweepMax = findViewById(R.id.seek_sweep_max)
        seekSweepSpeed = findViewById(R.id.seek_sweep_speed)
        seekBoxMin = findViewById(R.id.seek_box_min)
        seekBoxMax = findViewById(R.id.seek_box_max)
        seekBoxSpeed = findViewById(R.id.seek_box_speed)
        buttonApplySweepCfg = findViewById(R.id.button_apply_sweep_cfg)
        buttonApplyBoxCfg = findViewById(R.id.button_apply_box_cfg)

        textLogs = findViewById(R.id.text_logs)
        labelDisconnected = findViewById(R.id.label_disconnected)
        progressUpload = findViewById(R.id.progress_upload)
    }

    private fun setupSpinners() {
        val speedAdapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            speedOptions.map { "$it ms" }
        ).also {
            it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }
        spinnerSpeed.adapter = speedAdapter

        val ledAdapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            ledModes
        ).also {
            it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }
        spinnerSweepLed.adapter = ledAdapter
        spinnerBoxLed.adapter = ledAdapter
    }

    private fun setupObservers() {
        viewModel.status.observe(this) { status ->
            if (status == null) return@observe
            textRunning.text = if (status.running) "Running" else "Stopped"
            textDirection.text = status.direction
            textSpeed.text = "${status.speedMs} ms"
            textSweepLed.text = status.sweepLedMode
            textBoxLed.text = status.boxLedMode
            findViewById<TextView>(R.id.text_startup_sound).text =
                if (status.startupSound.isBlank()) "None" else status.startupSound

            val speedIndex = speedOptions.indexOf(status.speedMs)
            if (speedIndex >= 0) spinnerSpeed.setSelection(speedIndex)

            val sweepIndex = ledModes.indexOf(status.sweepLedMode)
            if (sweepIndex >= 0) spinnerSweepLed.setSelection(sweepIndex)

            val boxIndex = ledModes.indexOf(status.boxLedMode)
            if (boxIndex >= 0) spinnerBoxLed.setSelection(boxIndex)

            isMuted = status.muted == true || (status.muted is Boolean && status.muted)
            updateMuteButton()
        }

        viewModel.soundList.observe(this) { list ->
            val adapter = ArrayAdapter(
                this,
                android.R.layout.simple_spinner_item,
                list
            ).also {
                it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            }
            spinnerSounds.adapter = adapter
        }

        viewModel.logs.observe(this) { logs ->
            val builder = StringBuilder()
            logs.takeLast(50).forEach { entry ->
                val prefix = when (entry.direction) {
                    LogEntry.Direction.SENT -> ">> "
                    LogEntry.Direction.RECEIVED -> "<< "
                }
                builder.append(prefix).append(entry.text).append("\n")
            }
            textLogs.text = builder.toString()
        }

        viewModel.uploadInProgress.observe(this) { inProgress ->
            progressUpload.visibility = if (inProgress == true) android.view.View.VISIBLE else android.view.View.GONE
        }

        viewModel.uploadProgress.observe(this) { value ->
            progressUpload.progress = value ?: 0
        }

        viewModel.errorMessage.observe(this) { msg ->
            if (!msg.isNullOrEmpty()) {
                Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
            }
        }

        viewModel.disconnected.observe(this) { d ->
            labelDisconnected.visibility = if (d == true) android.view.View.VISIBLE else android.view.View.GONE
        }
    }

    private fun setupButtons() {
        buttonStart.setOnClickListener { viewModel.start() }
        buttonStop.setOnClickListener { viewModel.stop() }

        buttonDirUp.setOnClickListener { viewModel.dirUp() }
        buttonDirDown.setOnClickListener { viewModel.dirDown() }

        buttonFaster.setOnClickListener { viewModel.faster() }
        buttonSlower.setOnClickListener { viewModel.slower() }

        spinnerSpeed.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: AdapterView<*>?,
                view: android.view.View?,
                position: Int,
                id: Long
            ) {
                val ms = speedOptions[position]
                viewModel.setSpeed(ms)
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        spinnerSweepLed.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: AdapterView<*>?,
                view: android.view.View?,
                position: Int,
                id: Long
            ) {
                val mode = ledModes[position]
                viewModel.setSweepLedMode(mode)
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        spinnerBoxLed.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: AdapterView<*>?,
                view: android.view.View?,
                position: Int,
                id: Long
            ) {
                val mode = ledModes[position]
                viewModel.setBoxLedMode(mode)
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        buttonRefreshStatus.setOnClickListener { viewModel.refreshStatus() }

        buttonRefreshSounds.setOnClickListener { viewModel.refreshSounds() }

        buttonUploadSound.setOnClickListener {
            pickSoundLauncher.launch("audio/*")
        }

        buttonPlaySound.setOnClickListener {
            val selected = spinnerSounds.selectedItem as? String
            viewModel.playSound(selected)
        }

        buttonSetStartup.setOnClickListener {
            val selected = spinnerSounds.selectedItem as? String ?: return@setOnClickListener
            viewModel.setStartupSound(selected)
        }

        buttonSetRempod.setOnClickListener {
            Toast.makeText(this, "Rempod sound coming soon", Toast.LENGTH_SHORT).show()
        }

        buttonSetMusicbox.setOnClickListener {
            Toast.makeText(this, "Music box sound coming soon", Toast.LENGTH_SHORT).show()
        }

        buttonApplySweepCfg.setOnClickListener {
            val min = seekSweepMin.progress
            val max = seekSweepMax.progress
            val speed = seekSweepSpeed.progress + 1 // 1-10
            viewModel.setSweepConfig(min, max, speed)
        }

        buttonApplyBoxCfg.setOnClickListener {
            val min = seekBoxMin.progress
            val max = seekBoxMax.progress
            val speed = seekBoxSpeed.progress + 1 // 1-10
            viewModel.setBoxConfig(min, max, speed)
        }

        buttonDeviceSettings.setOnClickListener {
            val intent = android.content.Intent(this, com.apx.oraclebox.ui.settings.DeviceSettingsActivity::class.java).apply {
                putExtra(EXTRA_DEVICE_ADDRESS, intent.getStringExtra(EXTRA_DEVICE_ADDRESS))
                putExtra(EXTRA_DEVICE_NAME, intent.getStringExtra(EXTRA_DEVICE_NAME))
            }
            startActivity(intent)
        }

        buttonMute.setOnClickListener {
            val newMute = !isMuted
            val cmd = if (newMute) "MUTE ON" else "MUTE OFF"
            viewModel.sendCommand(cmd)
            isMuted = newMute
            updateMuteButton()
        }
    }

    private val pickSoundLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            val resolvedName = resolveDisplayName(uri)
                ?: uri.lastPathSegment?.substringAfterLast('/')
                ?: "sound_${System.currentTimeMillis()}.wav"
            contentResolver.openInputStream(uri)?.use { input ->
                val data = input.readBytes()
                viewModel.uploadSound(resolvedName, data)
            }
        }
    }

    private fun resolveDisplayName(uri: android.net.Uri): String? {
        val projection = arrayOf(OpenableColumns.DISPLAY_NAME)
        return contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
            val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && cursor.moveToFirst()) cursor.getString(idx) else null
        }
    }

    private fun updateMuteButton() {
        buttonMute.text = if (isMuted) "Unmute" else "Mute"
    }
}
