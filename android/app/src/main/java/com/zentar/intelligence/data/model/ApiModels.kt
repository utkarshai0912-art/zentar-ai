package com.zentar.intelligence.data.model

import com.google.gson.annotations.SerializedName

// ── Generic API Response ──
data class ApiResponse<T>(
    val success: Boolean = true,
    val message: String = "Success",
    val data: T? = null,
    val error: String? = null,
)

data class PaginatedResponse<T>(
    val items: List<T>,
    val total: Int,
    val page: Int,
    @SerializedName("page_size") val pageSize: Int,
    @SerializedName("total_pages") val totalPages: Int,
)

// ── Auth ──
data class AuthRegisterRequest(
    val email: String,
    val password: String,
    @SerializedName("display_name") val displayName: String,
)

data class AuthLoginRequest(
    val email: String,
    val password: String,
)

data class AuthRefreshRequest(
    @SerializedName("refresh_token") val refreshToken: String,
)

data class AuthTokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer",
    @SerializedName("expires_in") val expiresIn: Int = 900,
)

data class UserProfileResponse(
    val id: String,
    val email: String,
    @SerializedName("display_name") val displayName: String,
    @SerializedName("avatar_url") val avatarUrl: String? = null,
    val bio: String? = null,
    val role: String = "user",
    val theme: String = "system",
    val language: String = "en",
    @SerializedName("created_at") val createdAt: String,
)

// ── Conversations ──
data class ConversationCreateRequest(
    val title: String? = "New Conversation",
    @SerializedName("model_id") val modelId: String? = null,
    val provider: String? = null,
    @SerializedName("system_prompt") val systemPrompt: String? = null,
    val temperature: Double? = 0.7,
    @SerializedName("max_tokens") val maxTokens: Int? = 4096,
)

data class ConversationUpdateRequest(
    val title: String? = null,
    @SerializedName("is_archived") val isArchived: Boolean? = null,
    @SerializedName("is_pinned") val isPinned: Boolean? = null,
)

data class ConversationResponse(
    val id: String,
    val title: String,
    val messages: List<MessageResponse> = emptyList(),
    @SerializedName("model_id") val modelId: String? = null,
    val provider: String? = null,
    val temperature: Double = 0.7,
    @SerializedName("max_tokens") val maxTokens: Int = 4096,
    @SerializedName("is_archived") val isArchived: Boolean = false,
    @SerializedName("is_pinned") val isPinned: Boolean = false,
    @SerializedName("message_count") val messageCount: Int = 0,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String,
)

data class MessageResponse(
    val id: String,
    @SerializedName("conversation_id") val conversationId: String,
    val role: String,
    val content: String,
    @SerializedName("content_type") val contentType: String = "text",
    val status: String = "completed",
    val provider: String? = null,
    val model: String? = null,
    @SerializedName("created_at") val createdAt: String,
)

data class ChatRequest(
    val message: String,
    @SerializedName("conversation_id") val conversationId: String? = null,
    @SerializedName("model_id") val modelId: String? = null,
    val provider: String? = null,
    val stream: Boolean = true,
    val temperature: Double? = null,
    @SerializedName("max_tokens") val maxTokens: Int? = null,
    @SerializedName("system_prompt") val systemPrompt: String? = null,
)

// ── Models & Providers ──
data class ProvidersResponse(
    val providers: List<ProviderInfo>,
)

data class ProviderInfo(
    val id: String,
    val name: String,
    @SerializedName("display_name") val displayName: String,
    val description: String,
    @SerializedName("is_configured") val isConfigured: Boolean,
    @SerializedName("is_enabled") val isEnabled: Boolean,
)

data class ModelsResponse(
    val models: List<ModelInfo>,
)

data class ModelInfo(
    val id: String,
    val provider: String,
    val name: String,
    @SerializedName("display_name") val displayName: String? = null,
    @SerializedName("context_length") val contextLength: Int = 8192,
    @SerializedName("supports_streaming") val supportsStreaming: Boolean = true,
    @SerializedName("supports_reasoning") val supportsReasoning: Boolean = false,
    @SerializedName("is_default") val isDefault: Boolean = false,
    @SerializedName("is_enabled") val isEnabled: Boolean = true,
)

// ── Health ──
data class HealthResponse(
    val status: String,
    val version: String,
    val environment: String,
    val timestamp: Double,
)
