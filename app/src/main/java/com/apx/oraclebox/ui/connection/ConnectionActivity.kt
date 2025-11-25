package com.apx.oraclebox.ui.connection

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.lifecycle.ViewModelProvider
import com.apx.oraclebox.R
import com.apx.oraclebox.ui.control.ControlActivity

class ConnectionActivity : AppCompatActivity() {

    private lateinit var viewModel: ConnectionViewModel

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

        scanButton = findViewById(R.id.button_scan)
        deviceListView = findViewById(R.id.list_devices)
        statusText = findViewById(R.id.text_status)
        openControlsButton = findViewById(R.id.button_open_controls)
        progressBar = findViewById(R.id.progress_connecting)

        setupObservers()
        setupUi()
    }

    private fun setupObservers() {
        viewModel.pairedDevices.observe(this) { devices ->
            val names = devices.map { "${it.name} (${it.address})" }
            val adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, names)
            deviceListView.adapter = adapter
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
                startActivity(Intent(this, ControlActivity::class.java))
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

            // Launch controls screen with selected device details; ControlActivity will connect.
            val intent = Intent(this, ControlActivity::class.java).apply {
                putExtra(ControlActivity.EXTRA_DEVICE_ADDRESS, device.address)
                putExtra(ControlActivity.EXTRA_DEVICE_NAME, device.name)
            }
            startActivity(intent)
        }

        openControlsButton.setOnClickListener {
            startActivity(Intent(this, ControlActivity::class.java))
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
            } else {
                Toast.makeText(
                    this,
                    "Bluetooth permissions are required to connect to OracleBox.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
}
