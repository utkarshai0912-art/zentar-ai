package com.zentar.intelligence.data.repository

import com.zentar.intelligence.data.local.DataStoreManager
import com.zentar.intelligence.data.model.*
import com.zentar.intelligence.data.remote.ZentarApiService
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Zentar Intelligence — Auth Repository
 * Handles authentication, token management, and user profile.
 */
@Singleton
class AuthRepository @Inject constructor(
    private val api: ZentarApiService,
    private val dataStoreManager: DataStoreManager,
) {

    // ── Auth State ──
    val isLoggedIn: Flow<String?> = dataStoreManager.accessToken
    val currentUser: Flow<String?> = dataStoreManager.userDisplayName

    // ── Register ──
    suspend fun register(email: String, password: String, displayName: String): Result<AuthTokenResponse> {
        return try {
            val response = api.register(AuthRegisterRequest(email, password, displayName))
            if (response.isSuccessful && response.body()?.success == true) {
                val data = response.body()!!.data!!
                dataStoreManager.saveTokens(data.accessToken, data.refreshToken)
                Result.success(data)
            } else {
                Result.failure(Exception(response.body()?.error ?: "Registration failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Login ──
    suspend fun login(email: String, password: String): Result<AuthTokenResponse> {
        return try {
            val response = api.login(AuthLoginRequest(email, password))
            if (response.isSuccessful && response.body()?.success == true) {
                val data = response.body()!!.data!!
                dataStoreManager.saveTokens(data.accessToken, data.refreshToken)
                Result.success(data)
            } else {
                Result.failure(Exception(response.body()?.error ?: "Login failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Refresh Token ──
    suspend fun refreshToken(): Result<AuthTokenResponse> {
        return try {
            val currentRefresh = dataStoreManager.refreshToken.let { flow ->
                kotlinx.coroutines.flow.first { true }.let { flow }
            } ?: return Result.failure(Exception("No refresh token"))

            val response = api.refreshToken(AuthRefreshRequest(currentRefresh as String))
            if (response.isSuccessful && response.body()?.success == true) {
                val data = response.body()!!.data!!
                dataStoreManager.saveTokens(data.accessToken, data.refreshToken)
                Result.success(data)
            } else {
                Result.failure(Exception("Token refresh failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Get Profile ──
    suspend fun getProfile(): Result<UserProfileResponse> {
        return try {
            val response = api.getProfile()
            if (response.isSuccessful && response.body()?.success == true) {
                val data = response.body()!!.data!!
                dataStoreManager.saveUserInfo(data.id, data.email, data.displayName)
                Result.success(data)
            } else {
                Result.failure(Exception(response.body()?.error ?: "Failed to get profile"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Logout ──
    suspend fun logout() {
        dataStoreManager.clearTokens()
        dataStoreManager.clearUserInfo()
    }
}
