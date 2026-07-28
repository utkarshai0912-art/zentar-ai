package com.zentar.intelligence.data.repository

import com.zentar.intelligence.data.model.*
import com.zentar.intelligence.data.remote.ZentarApiService
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Zentar Intelligence — Chat Repository
 * Manages conversations, messages, and AI chat completions.
 */
@Singleton
class ChatRepository @Inject constructor(
    private val api: ZentarApiService,
) {

    // ── Conversations ──
    suspend fun getConversations(
        page: Int = 1,
        pageSize: Int = 20,
        archived: Boolean = false,
    ): Result<PaginatedResponse<ConversationResponse>> {
        return try {
            val response = api.getConversations(page, pageSize, archived)
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(response.body()!!.data!!)
            } else {
                Result.failure(Exception(response.body()?.error ?: "Failed to fetch conversations"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun createConversation(
        title: String? = null,
        modelId: String? = null,
        provider: String? = null,
        systemPrompt: String? = null,
    ): Result<ConversationResponse> {
        return try {
            val response = api.createConversation(
                ConversationCreateRequest(
                    title = title,
                    modelId = modelId,
                    provider = provider,
                    systemPrompt = systemPrompt,
                )
            )
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(response.body()!!.data!!)
            } else {
                Result.failure(Exception(response.body()?.error ?: "Failed to create conversation"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getConversation(id: String): Result<ConversationResponse> {
        return try {
            val response = api.getConversation(id)
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(response.body()!!.data!!)
            } else {
                Result.failure(Exception(response.body()?.error ?: "Failed to fetch conversation"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteConversation(id: String): Result<Unit> {
        return try {
            val response = api.deleteConversation(id)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Failed to delete conversation"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    // ── Models ──
    suspend fun getProviders(): Result<List<ProviderInfo>> {
        return try {
            val response = api.getProviders()
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(response.body()!!.data!!.providers)
            } else {
                Result.failure(Exception("Failed to fetch providers"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getAvailableModels(): Result<List<ModelInfo>> {
        return try {
            val response = api.getAvailableModels()
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(response.body()!!.data!!.models)
            } else {
                Result.failure(Exception("Failed to fetch models"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
