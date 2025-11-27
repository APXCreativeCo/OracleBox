package com.apx.oraclebox

import android.app.Application
import com.apx.oraclebox.bt.BluetoothRepository

/**
 * Application class to hold singleton Bluetooth repository
 * This ensures only one connection exists across all activities
 */
class OracleBoxApplication : Application() {
    
    companion object {
        private var bluetoothRepository: BluetoothRepository? = null
        
        fun getBluetoothRepository(deviceAddress: String?): BluetoothRepository? {
            return bluetoothRepository
        }
        
        fun setBluetoothRepository(repo: BluetoothRepository?) {
            bluetoothRepository = repo
        }
        
        fun clearBluetoothRepository() {
            bluetoothRepository?.disconnect()
            bluetoothRepository = null
        }
    }
}
