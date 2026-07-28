package com.zentar.intelligence.ui.navigation

import androidx.compose.animation.*
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

import com.zentar.intelligence.ui.screens.chat.ChatListScreen
import com.zentar.intelligence.ui.screens.chat.ChatScreen
import com.zentar.intelligence.ui.screens.home.HomeScreen
import com.zentar.intelligence.ui.screens.settings.SettingsScreen
import com.zentar.intelligence.ui.screens.plugins.PluginsScreen
import com.zentar.intelligence.ui.screens.skills.SkillsScreen
import com.zentar.intelligence.ui.screens.memory.MemoryScreen
import com.zentar.intelligence.ui.screens.files.FilesScreen

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    data object Home : Screen("home", "Home", Icons.Filled.Home)
    data object ChatList : Screen("chat_list", "Chat", Icons.Filled.Chat)
    data object Chat : Screen("chat/{conversationId}", "Chat", Icons.Filled.Chat)
    data object Settings : Screen("settings", "Settings", Icons.Filled.Settings)
    data object Plugins : Screen("plugins", "Plugins", Icons.Filled.Extension)
    data object Skills : Screen("skills", "Skills", Icons.Filled.SmartToy)
    data object Memory : Screen("memory", "Memory", Icons.Filled.Memory)
    data object Files : Screen("files", "Files", Icons.Filled.Folder)
}

val bottomNavItems = listOf(
    Screen.Home,
    Screen.ChatList,
    Screen.Plugins,
    Screen.Settings,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ZentarNavigation() {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    // Hide bottom bar on detail screens
    val showBottomBar = currentDestination?.route in bottomNavItems.map { it.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(
                    containerColor = MaterialTheme.colorScheme.surface,
                    contentColor = MaterialTheme.colorScheme.onSurface,
                ) {
                    bottomNavItems.forEach { screen ->
                        val selected = currentDestination?.hierarchy?.any {
                            it.route == screen.route
                        } == true

                        NavigationBarItem(
                            icon = {
                                Icon(screen.icon, contentDescription = screen.title)
                            },
                            label = { Text(screen.title, style = MaterialTheme.typography.labelSmall) },
                            selected = selected,
                            onClick = {
                                navController.navigate(screen.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = MaterialTheme.colorScheme.primary,
                                selectedTextColor = MaterialTheme.colorScheme.primary,
                                indicatorColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f),
                            ),
                        )
                    }
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Home.route,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable(Screen.Home.route) {
                HomeScreen(
                    onNavigateToChat = { navController.navigate(Screen.ChatList.route) },
                    onNavigateToSettings = { navController.navigate(Screen.Settings.route) },
                )
            }
            composable(Screen.ChatList.route) {
                ChatListScreen(
                    onConversationClick = { convId ->
                        navController.navigate("chat/$convId")
                    },
                    onNewChat = {
                        navController.navigate("chat/new")
                    },
                )
            }
            composable(Screen.Chat.route) {
                ChatScreen()
            }
            composable("chat/new") {
                ChatScreen()
            }
            composable(Screen.Settings.route) {
                SettingsScreen()
            }
            composable(Screen.Plugins.route) {
                PluginsScreen()
            }
            composable(Screen.Skills.route) {
                SkillsScreen()
            }
            composable(Screen.Memory.route) {
                MemoryScreen()
            }
            composable(Screen.Files.route) {
                FilesScreen()
            }
        }
    }
}
