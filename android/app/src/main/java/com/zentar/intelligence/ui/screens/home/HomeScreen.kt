package com.zentar.intelligence.ui.screens.home

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.zentar.intelligence.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onNavigateToChat: () -> Unit,
    onNavigateToSettings: () -> Unit,
) {
    val scrollBehavior = TopAppBarDefaults.pinnedScrollBehavior()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            "Zentar Intelligence",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            "Your AI Assistant",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings")
                    }
                },
                scrollBehavior = scrollBehavior,
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(androidx.compose.foundation.rememberScrollState()),
        ) {
            // Quick Action Buttons
            QuickActionSection(onNavigateToChat = onNavigateToChat)

            Spacer(modifier = Modifier.height(24.dp))

            // Features Grid
            FeaturesSection()

            Spacer(modifier = Modifier.height(24.dp))

            // Quick Stats
            QuickStatsSection()

            Spacer(modifier = Modifier.height(80.dp)) // Bottom nav padding
        }
    }
}

@Composable
private fun QuickActionSection(onNavigateToChat: () -> Unit) {
    Column(
        modifier = Modifier.padding(horizontal = 20.dp),
    ) {
        Text(
            "Quick Actions",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(bottom = 12.dp),
        )

        // Main chat button
        Button(
            onClick = onNavigateToChat,
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary,
            ),
        ) {
            Icon(Icons.Filled.AutoAwesome, contentDescription = null)
            Spacer(modifier = Modifier.width(12.dp))
            Text("Start a conversation", style = MaterialTheme.typography.titleMedium)
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Quick action chips
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val actions = listOf(
                "Code" to Icons.Filled.Code,
                "Search" to Icons.Filled.Search,
                "Analyze" to Icons.Filled.Analytics,
                "Write" to Icons.Filled.Edit,
            )
            items(actions) { (label, icon) ->
                AssistChip(
                    onClick = onNavigateToChat,
                    label = { Text(label) },
                    leadingIcon = {
                        Icon(icon, contentDescription = null, modifier = Modifier.size(18.dp))
                    },
                    shape = RoundedCornerShape(12.dp),
                )
            }
        }
    }
}

@Composable
private fun FeaturesSection() {
    Column(
        modifier = Modifier.padding(horizontal = 20.dp),
    ) {
        Text(
            "Features",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(bottom = 12.dp),
        )

        // Two-column grid
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FeatureCard(
                    icon = Icons.Filled.Extension,
                    title = "Plugins",
                    description = "Extend capabilities",
                    color = MaterialTheme.colorScheme.tertiary,
                    modifier = Modifier.weight(1f),
                )
                FeatureCard(
                    icon = Icons.Filled.SmartToy,
                    title = "Skills",
                    description = "AI expertise packs",
                    color = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.weight(1f),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FeatureCard(
                    icon = Icons.Filled.Memory,
                    title = "Memory",
                    description = "Context awareness",
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.weight(1f),
                )
                FeatureCard(
                    icon = Icons.Filled.Code,
                    title = "Coding",
                    description = "AI-powered IDE",
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun FeatureCard(
    icon: ImageVector,
    title: String,
    description: String,
    color: Color,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
        ) {
            Surface(
                shape = CircleShape,
                color = color.copy(alpha = 0.2f),
                modifier = Modifier.size(40.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        icon,
                        contentDescription = null,
                        tint = color,
                        modifier = Modifier.size(20.dp),
                    )
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun QuickStatsSection() {
    Column(
        modifier = Modifier.padding(horizontal = 20.dp),
    ) {
        Text(
            "System Status",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(bottom = 12.dp),
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            StatCard("Status", "Online", Modifier.weight(1f))
            StatCard("Model", "GPT-4o", Modifier.weight(1f))
            StatCard("Provider", "OpenAI", Modifier.weight(1f))
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
        ),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                value,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
