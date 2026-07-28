package com.zentar.intelligence.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import dagger.hilt.android.AndroidEntryPoint

/**
 * Zentar Intelligence — Notification Listener Service
 *
 * Listens for notifications to enable notification-based automation triggers.
 * Respects user privacy — notifications are only processed with explicit user authorization.
 */
@AndroidEntryPoint
class ZentarNotificationListener : NotificationListenerService() {

    companion object {
        var isRunning = false
            private set
        var lastNotification: StatusBarNotification? = null
            private set
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        isRunning = true
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        lastNotification = sbn
        // Process notification for automation triggers
        // e.g., trigger automation rule when specific app sends notification
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        // Notification was dismissed
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        isRunning = false
    }

    /**
     * Get the active notifications.
     */
    fun getActiveNotifications(): List<StatusBarNotification> {
        return try {
            activeNotifications?.toList() ?: emptyList()
        } catch (e: SecurityException) {
            emptyList()
        }
    }
}
