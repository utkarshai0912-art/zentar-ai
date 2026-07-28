# Zentar Intelligence ProGuard Rules

# Keep Retrofit interfaces
-keep,allowobfuscation interface com.zentar.intelligence.data.remote.*

# Keep Hilt
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }

# Keep Gson models
-keep class com.zentar.intelligence.data.model.** { *; }

# Keep Room entities
-keep class com.zentar.intelligence.data.local.entity.** { *; }

# Keep coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
