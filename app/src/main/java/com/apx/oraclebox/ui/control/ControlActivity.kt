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
    private lateinit var buttonStartSpiritBox: Button
    private lateinit var buttonBackToModes: Button

    private lateinit var seekSweepMin: SeekBar
    private lateinit var seekSweepMax: SeekBar
    private lateinit var seekSweepSpeed: SeekBar
    private lateinit var seekBoxMin: SeekBar
    private lateinit var seekBoxMax: SeekBar
    private lateinit var seekBoxSpeed: SeekBar
    private lateinit var buttonApplySweepCfg: Button
    private lateinit var buttonApplyBoxCfg: Button

    private lateinit var textLogs: TextView
    private lateinit var scrollLogs: ScrollView
    private lateinit var labelDisconnected: TextView

    // FX & Mixer controls
    private lateinit var switchFxEnabled: Switch
    private lateinit var textCurrentPreset: TextView
    private lateinit var buttonModeFM: Button
    private lateinit var buttonModeSB7: Button
    private lateinit var buttonSavePreset: Button
    private var currentMode: String = "FM" // FM or SB7
    private lateinit var sliderBpLow: SeekBar
    private lateinit var sliderBpHigh: SeekBar
    private lateinit var sliderContrast: SeekBar
    private lateinit var sliderReverb: SeekBar
    private lateinit var sliderGain: SeekBar
    private lateinit var sliderSpeakerVolume: SeekBar
    private lateinit var sliderMicVolume: SeekBar

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
    
    // Flags to prevent listener loops when updating UI programmatically
    private var isUpdatingFxUi = false
    private var isUpdatingMixerUi = false

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
        buttonStartSpiritBox = findViewById(R.id.button_start_spirit_box)
        buttonBackToModes = findViewById(R.id.button_back_to_modes_sb)

        // Initially hide sweep controls until START SPIRIT BOX is pressed
        hideSweepControls()

        seekSweepMin = findViewById(R.id.seek_sweep_min)
        seekSweepMax = findViewById(R.id.seek_sweep_max)
        seekSweepSpeed = findViewById(R.id.seek_sweep_speed)
        seekBoxMin = findViewById(R.id.seek_box_min)
        seekBoxMax = findViewById(R.id.seek_box_max)
        seekBoxSpeed = findViewById(R.id.seek_box_speed)
        buttonApplySweepCfg = findViewById(R.id.button_apply_sweep_cfg)
        buttonApplyBoxCfg = findViewById(R.id.button_apply_box_cfg)

        textLogs = findViewById(R.id.text_logs)
        scrollLogs = findViewById(R.id.scroll_logs)
        labelDisconnected = findViewById(R.id.label_disconnected)

        // FX & Mixer controls
        switchFxEnabled = findViewById(R.id.switch_fx_enabled)
        textCurrentPreset = findViewById(R.id.text_current_preset)
        buttonModeFM = findViewById(R.id.button_mode_fm)
        buttonModeSB7 = findViewById(R.id.button_mode_sb7)
        buttonSavePreset = findViewById(R.id.button_save_preset)
        sliderBpLow = findViewById(R.id.slider_bp_low)
        sliderBpHigh = findViewById(R.id.slider_bp_high)
        sliderContrast = findViewById(R.id.slider_contrast)
        sliderReverb = findViewById(R.id.slider_reverb)
        sliderGain = findViewById(R.id.slider_gain)
        sliderSpeakerVolume = findViewById(R.id.slider_speaker_volume)
        sliderMicVolume = findViewById(R.id.slider_mic_volume)
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
            
            // Auto-scroll to bottom to show newest logs
            scrollLogs.post {
                scrollLogs.fullScroll(ScrollView.FOCUS_DOWN)
            }
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

        // FX State Observer
        viewModel.fxUiState.observe(this) { state ->
            isUpdatingFxUi = true
            
            switchFxEnabled.isChecked = state.enabled
            textCurrentPreset.text = state.preset
            sliderBpLow.progress = (state.bpLowHz - 200).coerceIn(0, 800)
            sliderBpHigh.progress = (state.bpHighHz - 2000).coerceIn(0, 2000)
            sliderContrast.progress = state.contrast.coerceIn(0, 50)
            sliderReverb.progress = state.reverbLevel.coerceIn(0, 60)
            sliderGain.progress = (state.gainDb + 12).coerceIn(0, 24)
            
            // Disable FX sliders when FX is off (passthrough mode)
            sliderBpLow.isEnabled = state.enabled
            sliderBpHigh.isEnabled = state.enabled
            sliderContrast.isEnabled = state.enabled
            sliderReverb.isEnabled = state.enabled
            sliderGain.isEnabled = state.enabled
            buttonSavePreset.isEnabled = state.enabled && state.preset == "CUSTOM"
            
            // Highlight CUSTOM preset in different color
            if (state.preset == "CUSTOM") {
                textCurrentPreset.setTextColor(getColor(android.R.color.holo_orange_light))
            } else {
                textCurrentPreset.setTextColor(getColor(R.color.ghost_accent))
            }
            
            if (!state.error.isNullOrEmpty()) {
                Toast.makeText(this, "FX: ${state.error}", Toast.LENGTH_SHORT).show()
            }
            
            isUpdatingFxUi = false
        }

        // Mixer State Observer
        viewModel.mixerUiState.observe(this) { state ->
            isUpdatingMixerUi = true
            
            sliderSpeakerVolume.progress = state.speakerVolume.coerceIn(0, 37)
            sliderMicVolume.progress = state.micVolume.coerceIn(0, 35)
            
            if (!state.error.isNullOrEmpty()) {
                Toast.makeText(this, "Mixer: ${state.error}", Toast.LENGTH_SHORT).show()
            }
            
            isUpdatingMixerUi = false
        }

        // Load initial FX and Mixer status
        viewModel.loadFxStatus()
        viewModel.loadMixerStatus()
        viewModel.loadFxPresets()
        
        // Initialize mode buttons
        updateModeButtons()
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

        buttonStartSpiritBox.setOnClickListener {
            // Show sweep controls and start sweep
            showSweepControls()
            buttonStartSpiritBox.visibility = android.view.View.GONE
            viewModel.start()
        }

        buttonBackToModes.setOnClickListener {
            finish()
            overridePendingTransition(R.anim.fade_in_static, R.anim.fade_out_static)
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

        buttonMute.setOnClickListener {
            val newMute = !isMuted
            val cmd = if (newMute) "MUTE ON" else "MUTE OFF"
            viewModel.sendCommand(cmd)
            isMuted = newMute
            updateMuteButton()
        }

        // FX Controls
        switchFxEnabled.setOnCheckedChangeListener { _, isChecked ->
            if (!isUpdatingFxUi) {
                viewModel.setFxEnabled(isChecked)
            }
        }

        buttonModeFM.setOnClickListener {
            currentMode = "FM"
            updateModeButtons()
            showModePresetsDialog()
        }
        
        buttonModeSB7.setOnClickListener {
            currentMode = "SB7"
            updateModeButtons()
            showModePresetsDialog()
        }
        
        buttonSavePreset.setOnClickListener {
            showSavePresetDialog()
        }

        sliderBpLow.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingFxUi) {
                    val lowHz = (sliderBpLow.progress + 200)
                    val highHz = (sliderBpHigh.progress + 2000)
                    viewModel.updateBandpass(lowHz, highHz)
                }
            }
        })

        sliderBpHigh.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingFxUi) {
                    val lowHz = (sliderBpLow.progress + 200)
                    val highHz = (sliderBpHigh.progress + 2000)
                    viewModel.updateBandpass(lowHz, highHz)
                }
            }
        })

        sliderContrast.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingFxUi) {
                    viewModel.updateContrast(sliderContrast.progress)
                }
            }
        })

        sliderReverb.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingFxUi) {
                    viewModel.updateReverb(sliderReverb.progress)
                }
            }
        })

        sliderGain.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingFxUi) {
                    val gainDb = sliderGain.progress - 12
                    viewModel.updateGain(gainDb)
                }
            }
        })

        // Mixer Controls
        sliderSpeakerVolume.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingMixerUi) {
                    viewModel.setSpeakerVolume(sliderSpeakerVolume.progress)
                }
            }
        })

        sliderMicVolume.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                if (!isUpdatingMixerUi) {
                    viewModel.setMicVolume(sliderMicVolume.progress)
                }
            }
        })
    }

    private fun hideSweepControls() {
        findViewById<LinearLayout>(R.id.layout_status_cards)?.visibility = android.view.View.GONE
        findViewById<LinearLayout>(R.id.layout_sweep_buttons)?.visibility = android.view.View.GONE
        findViewById<LinearLayout>(R.id.layout_direction_buttons)?.visibility = android.view.View.GONE
    }

    private fun showSweepControls() {
        findViewById<LinearLayout>(R.id.layout_status_cards)?.visibility = android.view.View.VISIBLE
        findViewById<LinearLayout>(R.id.layout_sweep_buttons)?.visibility = android.view.View.VISIBLE
        findViewById<LinearLayout>(R.id.layout_direction_buttons)?.visibility = android.view.View.VISIBLE
    }

    private fun updateMuteButton() {
        buttonMute.text = if (isMuted) "Unmute" else "Mute"
    }

    private fun updateModeButtons() {
        val fmColor = if (currentMode == "FM") android.R.color.holo_green_light else android.R.color.darker_gray
        val sb7Color = if (currentMode == "SB7") android.R.color.holo_green_light else android.R.color.darker_gray
        buttonModeFM.setTextColor(getColor(fmColor))
        buttonModeSB7.setTextColor(getColor(sb7Color))
    }
    
    private fun showModePresetsDialog() {
        // Reload presets in case they weren't loaded yet
        viewModel.loadFxPresets()
        
        val presets = viewModel.fxPresets.value ?: emptyList()
        if (presets.isEmpty()) {
            Toast.makeText(this, "Loading presets...", Toast.LENGTH_SHORT).show()
            // Try again after a short delay
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                showModePresetsDialog()
            }, 500)
            return
        }

        // Filter presets by current mode
        val modePresets = presets.filter { it.category == currentMode }
        
        if (modePresets.isEmpty()) {
            Toast.makeText(this, "No ${currentMode} presets available", Toast.LENGTH_SHORT).show()
            return
        }

        // Build dialog items
        val items = modePresets.map { preset ->
            preset.name.replace("${currentMode}_", "").replace("_", " ")
        }.toTypedArray()

        android.app.AlertDialog.Builder(this)
            .setTitle("Select ${currentMode} Preset")
            .setItems(items) { _, which ->
                val selectedPreset = modePresets[which]
                viewModel.applyFxPreset(selectedPreset.name)
                Toast.makeText(
                    this,
                    "Applied: ${selectedPreset.name}",
                    Toast.LENGTH_SHORT
                ).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    private fun showSavePresetDialog() {
        val input = android.widget.EditText(this)
        input.hint = "Enter preset name"
        input.inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_CAP_WORDS
        
        android.app.AlertDialog.Builder(this)
            .setTitle("Save Custom Preset")
            .setMessage("Save current FX settings as a new ${currentMode} preset:")
            .setView(input)
            .setPositiveButton("Save") { _, _ ->
                val name = input.text.toString().trim()
                if (name.isEmpty()) {
                    Toast.makeText(this, "Please enter a preset name", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                // Format the preset name
                val presetName = "${currentMode}_${name.uppercase().replace(" ", "_")}"
                viewModel.saveCustomPreset(presetName, currentMode)
                Toast.makeText(this, "Saved: $presetName", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}
