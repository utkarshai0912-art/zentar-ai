package com.zentar.intelligence.ui.screens.skills

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class SkillCategory(
    val id: String,
    val name: String,
    val icon: @Composable () -> Unit,
)

data class SkillItem(
    val id: String,
    val name: String,
    val description: String,
    val category: String,
    val isEnabled: Boolean,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SkillsScreen() {
    val categories = remember {
        listOf(
            SkillCategory("all", "All", { Icon(Icons.Filled.AllInclusive, contentDescription = null) }),
            SkillCategory("coding", "Coding", { Icon(Icons.Filled.Code, contentDescription = null) }),
            SkillCategory("security", "Security", { Icon(Icons.Filled.Shield, contentDescription = null) }),
            SkillCategory("writing", "Writing", { Icon(Icons.Filled.Edit, contentDescription = null) }),
            SkillCategory("research", "Research", { Icon(Icons.Filled.Search, contentDescription = null) }),
            SkillCategory("data", "Data", { Icon(Icons.Filled.Analytics, contentDescription = null) }),
        )
    }

    val skills = remember {
        listOf(
            SkillItem("1", "Python Developer", "Expert Python coding, debugging, and optimization", "coding", true),
            SkillItem("2", "Penetration Testing", "Security assessment and vulnerability analysis", "security", false),
            SkillItem("3", "Content Writer", "SEO-optimized content creation and editing", "writing", true),
            SkillItem("4", "Research Assistant", "Deep research with citations and summaries", "research", true),
            SkillItem("5", "Data Analyst", "Data analysis, visualization, and insights", "data", false),
            SkillItem("6", "Android Developer", "Kotlin and Android app development", "coding", true),
        )
    }

    var selectedCategory by remember { mutableStateOf("all") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Skills", fontWeight = FontWeight.Bold) },
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
            // Category filter chips
            LazyRow(
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(categories) { category ->
                    FilterChip(
                        selected = selectedCategory == category.id,
                        onClick = { selectedCategory = category.id },
                        label = { Text(category.name) },
                        leadingIcon = { category.icon() },
                        shape = RoundedCornerShape(8.dp),
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            LazyColumn(
                contentPadding = PaddingValues(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(skills.filter { selectedCategory == "all" || it.category == selectedCategory }) { skill ->
                    SkillCard(skill = skill)
                }
            }
        }
    }
}

@Composable
private fun SkillCard(skill: SkillItem) {
    var enabled by remember(skill.id) { mutableStateOf(skill.isEnabled) }

    Card(
        modifier = Modifier.fillMaxWidth(),
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
                color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.15f),
                modifier = Modifier.size(44.dp),
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        Icons.Filled.SmartToy,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.secondary,
                        modifier = Modifier.size(22.dp),
                    )
                }
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    skill.name,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    skill.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Switch(
                checked = enabled,
                onCheckedChange = { enabled = it },
            )
        }
    }
}
