package com.zentar.intelligence.ui.screens.plugins

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

data class PluginItem(
    val id: String,
    val name: String,
    val description: String,
    val isEnabled: Boolean,
    val isOfficial: Boolean,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PluginsScreen() {
    val plugins = remember {
        listOf(
            PluginItem("1", "Web Search", "Search and retrieve web content", true, true),
            PluginItem("2", "File Manager", "Read, write, and manage files", true, true),
            PluginItem("3", "Code Analyzer", "Analyze and review source code", false, true),
            PluginItem("4", "Git Integration", "Version control operations", false, true),
            PluginItem("5", "Image Generator", "Generate images with AI", false, false),
            PluginItem("6", "Database Explorer", "Query and explore databases", false, false),
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Plugins", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                Text(
                    "Extend Zentar's capabilities with plugins.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
            }

            items(plugins) { plugin ->
                PluginCard(plugin = plugin)
            }
        }
    }
}

@Composable
private fun PluginCard(plugin: PluginItem) {
    var enabled by remember(plugin.id) { mutableStateOf(plugin.isEnabled) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { enabled = !enabled },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = if (enabled)
                    MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)
                else
                    MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.size(44.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        Icons.Filled.Extension,
                        contentDescription = null,
                        tint = if (enabled) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                        modifier = Modifier.size(22.dp),
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        plugin.name,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                    if (plugin.isOfficial) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                        ) {
                            Text(
                                "Official",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            )
                        }
                    }
                }
                Text(
                    plugin.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            Switch(
                checked = enabled,
                onCheckedChange = { enabled = it },
            )
        }
    }
}
