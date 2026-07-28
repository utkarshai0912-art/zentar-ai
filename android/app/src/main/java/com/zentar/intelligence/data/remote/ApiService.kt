package com.zentar.intelligence.data.remote

import com.zentar.intelligence.data.model.*
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

/**
 * Zentar Intelligence — Retrofit API Service
 * Defines all REST API endpoints for the backend.
 */
interface ZentarApiService {

    // ── Auth ──
    @POST("api/v1/auth/register")
    suspend fun register(@Body request: AuthRegisterRequest): Response<ApiResponse<AuthTokenResponse>>

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: AuthLoginRequest): Response<ApiResponse<AuthTokenResponse>>

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(@Body request: AuthRefreshRequest): Response<ApiResponse<AuthTokenResponse>>

    @GET("api/v1/auth/profile")
    suspend fun getProfile(): Response<ApiResponse<UserProfileResponse>>

    @PUT("api/v1/auth/profile")
    suspend fun updateProfile(@Body request: Map<String, String>): Response<ApiResponse<UserProfileResponse>>

    // ── Conversations ──
    @GET("api/v1/chat/conversations")
    suspend fun getConversations(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("archived") archived: Boolean = false,
    ): Response<ApiResponse<PaginatedResponse<ConversationResponse>>>

    @POST("api/v1/chat/conversations")
    suspend fun createConversation(@Body request: ConversationCreateRequest): Response<ApiResponse<ConversationResponse>>

    @GET("api/v1/chat/conversations/{id}")
    suspend fun getConversation(@Path("id") id: String): Response<ApiResponse<ConversationResponse>>

    @PUT("api/v1/chat/conversations/{id}")
    suspend fun updateConversation(
        @Path("id") id: String,
        @Body request: ConversationUpdateRequest,
    ): Response<ApiResponse<ConversationResponse>>

    @DELETE("api/v1/chat/conversations/{id}")
    suspend fun deleteConversation(@Path("id") id: String): Response<ApiResponse<Unit>>

    // ── Chat Streaming (SSE) ──
    @POST("api/v1/chat/completions")
    @Streaming
    suspend fun chatCompletion(@Body request: ChatRequest): Response<ResponseBody>

    // ── Models ──
    @GET("api/v1/models/providers")
    suspend fun getProviders(): Response<ApiResponse<ProvidersResponse>>

    @GET("api/v1/models/available")
    suspend fun getAvailableModels(): Response<ApiResponse<ModelsResponse>>

    @GET("api/v1/models/providers/{provider}/models")
    suspend fun getProviderModels(@Path("provider") provider: String): Response<ApiResponse<ModelsResponse>>

    // ── Health ──
    @GET("health")
    suspend fun healthCheck(): Response<HealthResponse>
}
