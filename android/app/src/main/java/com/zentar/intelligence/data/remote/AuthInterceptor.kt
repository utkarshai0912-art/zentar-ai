package com.zentar.intelligence.data.remote

import com.zentar.intelligence.data.local.DataStoreManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Zentar Intelligence — OkHttp Auth Interceptor
 * Automatically attaches Bearer token to authenticated requests.
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val dataStoreManager: DataStoreManager,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        // Skip auth for non-API requests
        if (!originalRequest.url.encodedPath.contains("/api/")) {
            return chain.proceed(originalRequest)
        }

        // Skip auth for auth endpoints (register, login, refresh)
        if (originalRequest.url.encodedPath.contains("/auth/")) {
            return chain.proceed(originalRequest)
        }

        val token = runBlocking {
            dataStoreManager.accessToken.first()
        }

        if (token.isNullOrBlank()) {
            return chain.proceed(originalRequest)
        }

        val authenticatedRequest = originalRequest.newBuilder()
            .header("Authorization", "Bearer $token")
            .build()

        return chain.proceed(authenticatedRequest)
    }
}
