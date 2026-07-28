package com.zentar.intelligence.ui.screens.memory

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

data class MemoryItem(
    val id: String,
    val content: String,
    val type: String, // conversation, long_term, note, pinned
    val date: String,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MemoryScreen() {
    var searchQuery by remember { mutableStateOf("") }

    val memories = remember {
        listOf(
            MemoryItem("1", "User prefers Python for backend development", "pinned", "2 days ago"),
            MemoryItem("2", "Working on a FastAPI project with PostgreSQL", "conversation", "3 days ago"),
            MemoryItem("3", "User's preferred code editor is VS Code", "long_term", "1 week ago"),
            MemoryItem("4", "Meeting notes: Project architecture review", "note", "5 days ago"),
            MemoryItem("5", "API design preferences: REST over GraphQL", "long_term", "2 weeks ago"),
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Memory", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            // Search bar
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                placeholder = { Text("Search memories...") },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { searchQuery = "" }) {
                            Icon(Icons.Filled.Clear, contentDescription = "Clear")
                        }
                    }
                },
                shape = RoundedCornerShape(12.dp),
                singleLine = true,
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Filter chips
            Row(
                modifier = Modifier.padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                AssistChip(onClick = {}, label = { Text("All") }, shape = RoundedCornerShape(8.dp))
                AssistChip(onClick = {}, label = { Text("Pinned") }, shape = RoundedCornerShape(8.dp))
                AssistChip(onClick = {}, label = { Text("Notes") }, shape = RoundedCornerShape(8.dp))
                AssistChip(onClick = {}, label = { Text("Long-term") }, shape = RoundedCornerShape(8.dp))
            }

            Spacer(modifier = Modifier.height(12.dp))

            LazyColumn(
                contentPadding = PaddingValues(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(memories) { memory ->
                    MemoryCard(memory = memory)
                }
            }
        }
    }
}

@Composable
private fun MemoryCard(memory: MemoryItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    when (memory.type) {
                        "pinned" -> Icons.Filled.PushPin
                        "note" -> Icons.Filled.Note
                        "long_term" -> Icons.Filled.History
                        else -> Icons.Filled.Chat
                    },
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    memory.content,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    memory.type.replace("_", " ").replaceFirstChar { it.uppercase() },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    memory.date,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                )
            }
        }
    }
}
