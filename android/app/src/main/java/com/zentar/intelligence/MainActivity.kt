package com.zentar.intelligence

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.zentar.intelligence.data.local.DataStoreManager
import com.zentar.intelligence.ui.navigation.ZentarNavigation
import com.zentar.intelligence.ui.theme.ZentarTheme
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

/**
 * Zentar Intelligence — Main Activity
 * Single-activity architecture with Jetpack Compose navigation.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var dataStoreManager: DataStoreManager

    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)

        enableEdgeToEdge()

        setContent {
            val darkMode by dataStoreManager.darkMode.collectAsState(initial = false)
            val dynamicColors by dataStoreManager.dynamicColors.collectAsState(initial = true)

            ZentarTheme(
                darkTheme = darkMode,
                dynamicColor = dynamicColors,
            ) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    ZentarNavigation()
                }
            }
        }
    }
}
