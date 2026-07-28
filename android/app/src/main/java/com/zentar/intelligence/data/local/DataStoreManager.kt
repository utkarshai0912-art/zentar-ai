package com.zentar.intelligence.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "zentar_prefs")

/**
 * Zentar Intelligence — DataStore Manager
 * Manages local preferences and authentication tokens securely.
 */
class DataStoreManager(private val context: Context) {

    companion object {
        private val ACCESS_TOKEN = stringPreferencesKey("access_token")
        private val REFRESH_TOKEN = stringPreferencesKey("refresh_token")
        private val USER_ID = stringPreferencesKey("user_id")
        private val USER_EMAIL = stringPreferencesKey("user_email")
        private val USER_DISPLAY_NAME = stringPreferencesKey("user_display_name")
        private val DARK_MODE = booleanPreferencesKey("dark_mode")
        private val DYNAMIC_COLORS = booleanPreferencesKey("dynamic_colors")
        private val SELECTED_MODEL = stringPreferencesKey("selected_model")
        private val SELECTED_PROVIDER = stringPreferencesKey("selected_provider")
        private val TEMPERATURE = floatPreferencesKey("temperature")
        private val MAX_TOKENS = intPreferencesKey("max_tokens")
        private val FIRST_LAUNCH = booleanPreferencesKey("first_launch")
        private val ONBOARDING_COMPLETE = booleanPreferencesKey("onboarding_complete")
    }

    // ── Auth Tokens ──
    val accessToken: Flow<String?> = context.dataStore.data.map { it[ACCESS_TOKEN] }
    val refreshToken: Flow<String?> = context.dataStore.data.map { it[REFRESH_TOKEN] }

    suspend fun saveTokens(access: String, refresh: String) {
        context.dataStore.edit {
            it[ACCESS_TOKEN] = access
            it[REFRESH_TOKEN] = refresh
        }
    }

    suspend fun clearTokens() {
        context.dataStore.edit {
            it.remove(ACCESS_TOKEN)
            it.remove(REFRESH_TOKEN)
        }
    }

    // ── User Info ──
    val userId: Flow<String?> = context.dataStore.data.map { it[USER_ID] }
    val userEmail: Flow<String?> = context.dataStore.data.map { it[USER_EMAIL] }
    val userDisplayName: Flow<String?> = context.dataStore.data.map { it[USER_DISPLAY_NAME] }

    suspend fun saveUserInfo(id: String, email: String, displayName: String) {
        context.dataStore.edit {
            it[USER_ID] = id
            it[USER_EMAIL] = email
            it[USER_DISPLAY_NAME] = displayName
        }
    }

    suspend fun clearUserInfo() {
        context.dataStore.edit {
            it.remove(USER_ID)
            it.remove(USER_EMAIL)
            it.remove(USER_DISPLAY_NAME)
        }
    }

    // ── Theme ──
    val darkMode: Flow<Boolean> = context.dataStore.data.map { it[DARK_MODE] ?: false }
    val dynamicColors: Flow<Boolean> = context.dataStore.data.map { it[DYNAMIC_COLORS] ?: true }

    suspend fun setDarkMode(enabled: Boolean) {
        context.dataStore.edit { it[DARK_MODE] = enabled }
    }

    suspend fun setDynamicColors(enabled: Boolean) {
        context.dataStore.edit { it[DYNAMIC_COLORS] = enabled }
    }

    // ── Model Settings ──
    val selectedModel: Flow<String?> = context.dataStore.data.map { it[SELECTED_MODEL] }
    val selectedProvider: Flow<String?> = context.dataStore.data.map { it[SELECTED_PROVIDER] }
    val temperature: Flow<Float> = context.dataStore.data.map { it[TEMPERATURE] ?: 0.7f }
    val maxTokens: Flow<Int> = context.dataStore.data.map { it[MAX_TOKENS] ?: 4096 }

    suspend fun setSelectedModel(model: String) {
        context.dataStore.edit { it[SELECTED_MODEL] = model }
    }

    suspend fun setSelectedProvider(provider: String) {
        context.dataStore.edit { it[SELECTED_PROVIDER] = provider }
    }

    suspend fun setTemperature(temp: Float) {
        context.dataStore.edit { it[TEMPERATURE] = temp }
    }

    suspend fun setMaxTokens(tokens: Int) {
        context.dataStore.edit { it[MAX_TOKENS] = tokens }
    }

    // ── Onboarding ──
    val isFirstLaunch: Flow<Boolean> = context.dataStore.data.map { it[FIRST_LAUNCH] ?: true }
    val isOnboardingComplete: Flow<Boolean> = context.dataStore.data.map { it[ONBOARDING_COMPLETE] ?: false }

    suspend fun setOnboardingComplete() {
        context.dataStore.edit {
            it[FIRST_LAUNCH] = false
            it[ONBOARDING_COMPLETE] = true
        }
    }

    // ── Clear All ──
    suspend fun clearAll() {
        context.dataStore.edit { it.clear() }
    }
}
