package com.apx.oraclebox

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.apx.oraclebox.ui.connection.ConnectionActivity

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Immediately forward to the themed connection screen and finish
        startActivity(Intent(this, ConnectionActivity::class.java))
        finish()
    }
}