package com.apx.oraclebox.ui.connection

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.animation.AnimationUtils
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.mode.ModeSelectionActivity

class ConnectionActivity : AppCompatActivity() {

    companion object {
        private const val PREFS_NAME = "OracleBoxPrefs"
        private const val KEY_SAVED_DEVICE_ADDRESS = "saved_device_address"
        private const val KEY_SAVED_DEVICE_NAME = "saved_device_name"
    }

    private lateinit var viewModel: ConnectionViewModel

    private lateinit var logoImageView: ImageView
    private lateinit var scanButton: Button
    private lateinit var deviceListView: ListView
    private lateinit var statusText: TextView
    private lateinit var openControlsButton: Button
    private lateinit var progressBar: ProgressBar

    private val bluetoothAdapter: BluetoothAdapter? by lazy {
        BluetoothAdapter.getDefaultAdapter()
    }

    private val enableBtLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        viewModel.refreshPairedDevices()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_connection)

        viewModel = ViewModelProvider(this)[ConnectionViewModel::class.java]

        logoImageView = findViewById(R.id.image_logo4)
        scanButton = findViewById(R.id.button_scan)
        deviceListView = findViewById(R.id.list_devices)
        statusText = findViewById(R.id.text_status)
        openControlsButton = findViewById(R.id.button_open_controls)
        progressBar = findViewById(R.id.progress_connecting)

        setupObservers()
        setupUi()
        attemptAutoConnect()
    }

    private fun setupObservers() {
        viewModel.pairedDevices.observe(this) { devices ->
            val names = devices.map { "${it.name} (${it.address})" }
            val adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, names)
            deviceListView.adapter = adapter
            
            // Set ListView height based on content to work inside ScrollView
            setListViewHeightBasedOnChildren(deviceListView)
        }

        viewModel.connectionStatus.observe(this) {
            statusText.text = it
        }

        viewModel.isConnecting.observe(this) { connecting ->
            progressBar.visibility = if (connecting) android.view.View.VISIBLE else android.view.View.GONE
        }

        viewModel.errorMessage.observe(this) { msg ->
            if (!msg.isNullOrEmpty()) {
                Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
            }
        }

        viewModel.navigateToControl.observe(this) { navigate ->
            if (navigate == true) {
                viewModel.onNavigatedToControl()
                startActivity(Intent(this, ModeSelectionActivity::class.java))
            }
        }
    }

    private fun setupUi() {
        scanButton.setOnClickListener {
            if (ensureBluetoothPermissions()) {
                viewModel.refreshPairedDevices()
            }
        }

        deviceListView.setOnItemClickListener { _, _, position, _ ->
            val devices = viewModel.pairedDevices.value ?: return@setOnItemClickListener
            val device = devices.getOrNull(position) ?: return@setOnItemClickListener

            if (!ensureBluetoothPermissions()) {
                Toast.makeText(this, "Bluetooth permission required", Toast.LENGTH_SHORT).show()
                return@setOnItemClickListener
            }

            // Save device for auto-connect
            saveDevicePreference(device.address, device.name ?: "OracleBox")

            // Launch mode selection screen with selected device details
            val intent = Intent(this, ModeSelectionActivity::class.java).apply {
                putExtra(ModeSelectionActivity.EXTRA_DEVICE_ADDRESS, device.address)
                putExtra(ModeSelectionActivity.EXTRA_DEVICE_NAME, device.name)
            }
            startActivity(intent)
            overridePendingTransition(R.anim.slide_in_right, R.anim.slide_out_left)
        }

        openControlsButton.setOnClickListener {
            startActivity(Intent(this, ModeSelectionActivity::class.java))
        }
    }

    private fun ensureBluetoothPermissions(): Boolean {
        val needs = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ActivityCompat.checkSelfPermission(
                    this,
                    Manifest.permission.BLUETOOTH_SCAN
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                needs.add(Manifest.permission.BLUETOOTH_SCAN)
            }
            if (ActivityCompat.checkSelfPermission(
                    this,
                    Manifest.permission.BLUETOOTH_CONNECT
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                needs.add(Manifest.permission.BLUETOOTH_CONNECT)
            }
        } else {
            if (ActivityCompat.checkSelfPermission(
                    this,
                    Manifest.permission.ACCESS_FINE_LOCATION
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                needs.add(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }

        return if (needs.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needs.toTypedArray(), 1001)
            false
        } else {
            true
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1001) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                viewModel.refreshPairedDevices()
                // Try auto-connect again now that we have permissions
                attemptAutoConnect()
            } else {
                Toast.makeText(
                    this,
                    "Bluetooth permissions are required to connect to OracleBox.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
    
    private fun setListViewHeightBasedOnChildren(listView: ListView) {
        val listAdapter = listView.adapter ?: return
        var totalHeight = 0
        for (i in 0 until listAdapter.count) {
            val listItem = listAdapter.getView(i, null, listView)
            listItem.measure(0, 0)
            totalHeight += listItem.measuredHeight
        }
        
        val params = listView.layoutParams
        params.height = totalHeight + (listView.dividerHeight * (listAdapter.count - 1))
        listView.layoutParams = params
        listView.requestLayout()
    }

    private fun attemptAutoConnect() {
        // Check if we have permissions without requesting them
        val hasPermissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ActivityCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
        } else {
            ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        }
        
        if (!hasPermissions) {
            // Don't auto-connect if we don't have permissions yet
            return
        }

        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val savedAddress = prefs.getString(KEY_SAVED_DEVICE_ADDRESS, null)
        val savedName = prefs.getString(KEY_SAVED_DEVICE_NAME, null)

        if (savedAddress != null) {
            // Start loading animation
            startLoadingAnimation()
            
            // Try to find saved device in paired devices
            val adapter = bluetoothAdapter ?: run {
                stopLoadingAnimation()
                statusText.text = "Bluetooth not available"
                return
            }
            
            // Simulate connection attempt with delay for visual effect
            Handler(Looper.getMainLooper()).postDelayed({
                try {
                    val device = adapter.bondedDevices?.find { it.address == savedAddress }
                    
                    if (device != null) {
                        // Found saved device, connect automatically
                        statusText.text = "Connected to ${savedName ?: device.name}!"
                        
                        // Start swoop animation then navigate
                        Handler(Looper.getMainLooper()).postDelayed({
                            val finalName = device.name ?: savedName ?: "OracleBox"
                            startSwoopTransition(device.address, finalName)
                        }, 300)
                    } else {
                        // Saved device not found in paired devices
                        stopLoadingAnimation()
                        statusText.text = "Saved device not found. Please scan for devices."
                        Toast.makeText(
                            this,
                            "Could not find saved device. Please scan and select your device.",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                } catch (e: SecurityException) {
                    // Permission not granted yet
                    stopLoadingAnimation()
                    statusText.text = "Bluetooth permission required"
                }
            }, 1500) // 1.5 second loading animation
        }
    }

    private fun startLoadingAnimation() {
        // Hide UI elements
        scanButton.visibility = View.GONE
        deviceListView.visibility = View.GONE
        findViewById<TextView>(R.id.text_devices_label).visibility = View.GONE
        openControlsButton.visibility = View.GONE
        
        // Show progress and status
        progressBar.visibility = View.VISIBLE
        statusText.text = "Connecting to OracleBox..."
        
        // Start pulsing logo animation
        val pulseAnim = AnimationUtils.loadAnimation(this, R.anim.pulse_logo)
        logoImageView.startAnimation(pulseAnim)
    }

    private fun stopLoadingAnimation() {
        // Show UI elements again
        scanButton.visibility = View.VISIBLE
        deviceListView.visibility = View.VISIBLE
        findViewById<TextView>(R.id.text_devices_label).visibility = View.VISIBLE
        
        // Hide progress
        progressBar.visibility = View.GONE
        
        // Stop logo animation
        logoImageView.clearAnimation()
    }

    private fun startSwoopTransition(deviceAddress: String, deviceName: String) {
        // Load swoop animation
        val swoopAnim = AnimationUtils.loadAnimation(this, R.anim.zoom_swoop)
        
        // Start animation on entire root layout
        findViewById<LinearLayout>(R.id.layout_connection_root).startAnimation(swoopAnim)
        
        // Navigate after animation completes
        Handler(Looper.getMainLooper()).postDelayed({
            val intent = Intent(this, ModeSelectionActivity::class.java).apply {
                putExtra(ModeSelectionActivity.EXTRA_DEVICE_ADDRESS, deviceAddress)
                putExtra(ModeSelectionActivity.EXTRA_DEVICE_NAME, deviceName)
            }
            startActivity(intent)
            // Disable return animation for smooth transition
            overridePendingTransition(0, 0)
        }, 500) // Match animation duration
    }

    private fun saveDevicePreference(address: String, name: String) {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().apply {
            putString(KEY_SAVED_DEVICE_ADDRESS, address)
            putString(KEY_SAVED_DEVICE_NAME, name)
            apply()
        }
    }

    fun clearSavedDevice() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().apply {
            remove(KEY_SAVED_DEVICE_ADDRESS)
            remove(KEY_SAVED_DEVICE_NAME)
            apply()
        }
    }
}
