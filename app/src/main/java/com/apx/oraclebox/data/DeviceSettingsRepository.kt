package com.apx.oraclebox.data

import android.content.Context
import android.content.SharedPreferences

class DeviceSettingsRepository(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("oraclebox_device_settings", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_PI_BASE_URL = "pi_base_url"
        private const val DEFAULT_PI_BASE_URL = "http://192.168.1.74:5000"
    }

    fun getPiBaseUrl(): String =
        prefs.getString(KEY_PI_BASE_URL, DEFAULT_PI_BASE_URL) ?: DEFAULT_PI_BASE_URL

    fun setPiBaseUrl(url: String) {
        prefs.edit().putString(KEY_PI_BASE_URL, url.trim()).apply()
    }
}
