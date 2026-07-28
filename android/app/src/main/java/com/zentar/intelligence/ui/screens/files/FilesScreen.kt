package com.zentar.intelligence.ui.screens.files

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

data class FileItem(
    val name: String,
    val type: String, // file, folder
    val extension: String? = null,
    val size: String? = null,
    val modified: String? = null,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FilesScreen() {
    val files = remember {
        listOf(
            FileItem("Projects", "folder"),
            FileItem("Documents", "folder"),
            FileItem("Downloads", "folder"),
            FileItem("README.md", "file", ".md", "2.1 KB", "1 day ago"),
            FileItem("main.py", "file", ".py", "4.5 KB", "2 days ago"),
            FileItem("config.json", "file", ".json", "1.2 KB", "3 days ago"),
            FileItem("notes.txt", "file", ".txt", "0.8 KB", "5 days ago"),
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Files", fontWeight = FontWeight.Bold) },
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
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            items(files) { file ->
                FileRow(file = file)
            }
        }
    }
}

@Composable
private fun FileRow(file: FileItem) {
    val icon = when {
        file.type == "folder" -> Icons.Filled.Folder
        file.extension == ".py" -> Icons.Filled.Code
        file.extension == ".md" -> Icons.Filled.Description
        file.extension == ".json" -> Icons.Filled.DataObject
        file.extension == ".txt" -> Icons.Filled.TextSnippet
        else -> Icons.Filled.InsertDriveFile
    }

    val tint = when {
        file.type == "folder" -> MaterialTheme.colorScheme.primary
        file.extension == ".py" -> MaterialTheme.colorScheme.tertiary
        file.extension == ".md" -> MaterialTheme.colorScheme.secondary
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { /* Open file */ },
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f),
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = tint,
                modifier = Modifier.size(24.dp),
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    file.name,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = if (file.type == "folder") FontWeight.SemiBold else FontWeight.Normal,
                )
                if (file.size != null) {
                    Text(
                        "${file.size} · ${file.modified}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                    )
                }
            }
            IconButton(onClick = { /* More options */ }) {
                Icon(
                    Icons.Filled.MoreVert,
                    contentDescription = "Options",
                    modifier = Modifier.size(18.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}
