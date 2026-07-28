package com.zentar.intelligence

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

/**
 * Zentar Intelligence — Application class
 * Initializes Hilt dependency injection and global configuration.
 */
@HiltAndroidApp
class ZentarApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    companion object {
        lateinit var instance: ZentarApplication
            private set
    }
}
