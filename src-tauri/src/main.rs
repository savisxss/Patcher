// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::process::{Child, Command, Stdio};
use std::sync::Arc;
use tauri::{AppHandle, Manager, State};
use tokio::sync::Mutex;

#[derive(Serialize, Deserialize, Clone)]
struct AppConfig {
    #[serde(rename = "serverUrl")]
    server_url: String,
    #[serde(rename = "targetFolder")]
    target_folder: String,
    #[serde(rename = "fileListUrl")]
    file_list_url: String,
    #[serde(rename = "downloadSpeedLimit")]
    download_speed_limit: u64,
}

#[derive(Serialize, Deserialize, Clone)]
struct StatusReport {
    updated: Vec<String>,
    skipped: Vec<String>,
    failed: Vec<String>,
    verification: VerificationReport,
}

#[derive(Serialize, Deserialize, Clone)]
struct VerificationReport {
    verified: Vec<String>,
    corrupted: Vec<String>,
}

#[derive(Serialize, Deserialize)]
struct ProgressData {
    progress: usize,
    total: usize,
    logs: Vec<LogEntry>,
    completed: bool,
    error: Option<String>,
    status_report: Option<StatusReport>,
}

#[derive(Serialize, Deserialize, Clone)]
struct LogEntry {
    message: String,
    #[serde(rename = "type")]
    log_type: String,
}

// State to track the Python backend process
struct BackendProcess(Arc<Mutex<Option<Child>>>);

#[tauri::command]
async fn start_backend(
    backend_process: State<'_, BackendProcess>,
    app_handle: AppHandle,
) -> Result<String, String> {
    let mut process_guard = backend_process.0.lock().await;

    // Check if process is already running
    if let Some(ref mut child) = *process_guard {
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited, we can start a new one
                *process_guard = None;
            }
            Ok(None) => {
                // Process is still running
                return Ok("Backend already running".to_string());
            }
            Err(_) => {
                // Error checking process, assume it's not running
                *process_guard = None;
            }
        }
    }

    // Start the Python backend
    match Command::new("python")
        .arg("python_backend.py")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
    {
        Ok(child) => {
            *process_guard = Some(child);

            // Wait a bit for the server to start
            tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

            // Emit event to frontend
            let _ = app_handle.emit_all("backend_started", ());

            Ok("Backend started successfully".to_string())
        }
        Err(e) => Err(format!("Failed to start backend: {}", e)),
    }
}

#[tauri::command]
async fn stop_backend(backend_process: State<'_, BackendProcess>) -> Result<String, String> {
    let mut process_guard = backend_process.0.lock().await;

    if let Some(mut child) = process_guard.take() {
        match child.kill() {
            Ok(_) => {
                let _ = child.wait(); // Clean up zombie process
                Ok("Backend stopped".to_string())
            }
            Err(e) => Err(format!("Failed to stop backend: {}", e)),
        }
    } else {
        Ok("Backend was not running".to_string())
    }
}

#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    let client = reqwest::Client::new();

    match client
        .get("http://localhost:8080/health")
        .timeout(tokio::time::Duration::from_secs(5))
        .send()
        .await
    {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

#[tauri::command]
async fn load_config() -> Result<AppConfig, String> {
    let client = reqwest::Client::new();

    match client
        .get("http://localhost:8080/config")
        .timeout(tokio::time::Duration::from_secs(10))
        .send()
        .await
    {
        Ok(response) => match response.json::<AppConfig>().await {
            Ok(config) => Ok(config),
            Err(e) => Err(format!("Failed to parse config: {}", e)),
        },
        Err(e) => Err(format!("Failed to load config: {}", e)),
    }
}

#[tauri::command]
async fn save_config(config: AppConfig) -> Result<String, String> {
    let client = reqwest::Client::new();

    match client
        .post("http://localhost:8080/config")
        .json(&config)
        .timeout(tokio::time::Duration::from_secs(10))
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                Ok("Configuration saved".to_string())
            } else {
                Err("Failed to save configuration".to_string())
            }
        }
        Err(e) => Err(format!("Failed to save config: {}", e)),
    }
}

#[tauri::command]
async fn start_update(
    app_handle: AppHandle,
    config: AppConfig,
) -> Result<String, String> {
    let client = reqwest::Client::new();

    let request_data = serde_json::json!({
        "config": config
    });

    // Start the update process
    match client
        .post("http://localhost:8080/update")
        .json(&request_data)
        .timeout(tokio::time::Duration::from_secs(10))
        .send()
        .await
    {
        Ok(response) => {
            if response.status().is_success() {
                // Start polling for status updates
                let app_handle_clone = app_handle.clone();
                tokio::spawn(async move {
                    poll_update_status(app_handle_clone).await;
                });

                Ok("Update started".to_string())
            } else {
                Err("Failed to start update".to_string())
            }
        }
        Err(e) => Err(format!("Failed to start update: {}", e)),
    }
}

async fn poll_update_status(app_handle: AppHandle) {
    let client = reqwest::Client::new();
    let mut last_log_count = 0;

    loop {
        match client
            .get("http://localhost:8080/status")
            .timeout(tokio::time::Duration::from_secs(5))
            .send()
            .await
        {
            Ok(response) => {
                if let Ok(status) = response.json::<ProgressData>().await {
                    // Emit progress update
                    let _ = app_handle.emit_all("update_progress", serde_json::json!({
                        "progress": status.progress,
                        "total": status.total
                    }));

                    // Emit new log messages
                    if status.logs.len() > last_log_count {
                        for log in &status.logs[last_log_count..] {
                            let _ = app_handle.emit_all("log_message", log);
                        }
                        last_log_count = status.logs.len();
                    }

                    // Check if update is complete
                    if status.completed {
                        if let Some(report) = status.status_report {
                            let _ = app_handle.emit_all("update_complete", report);
                        }

                        if let Some(error) = status.error {
                            let _ = app_handle.emit_all("update_error", error);
                        }
                        break;
                    }
                }
            }
            Err(_) => {
                // If we can't reach the backend, stop polling
                break;
            }
        }

        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    }
}

#[tauri::command]
async fn close_app(app_handle: AppHandle, backend_process: State<'_, BackendProcess>) -> Result<(), String> {
    // Stop the backend first
    let _ = stop_backend(backend_process).await;

    // Then exit the app
    app_handle.exit(0);
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(BackendProcess(Arc::new(Mutex::new(None))))
        .invoke_handler(tauri::generate_handler![
            start_backend,
            stop_backend,
            check_backend_health,
            load_config,
            save_config,
            start_update,
            close_app
        ])
        .setup(|app| {
            let app_handle = app.handle();

            // Auto-start the backend when the app starts
            tauri::async_runtime::spawn(async move {
                let backend_process = app_handle.state::<BackendProcess>();
                let _ = start_backend(backend_process, app_handle).await;
            });

            Ok(())
        })
        .on_window_event(|event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event.event() {
                // Clean up backend process when window closes
                let app_handle = event.window().app_handle();
                let backend_process = app_handle.state::<BackendProcess>();

                tauri::async_runtime::spawn(async move {
                    let _ = stop_backend(backend_process).await;
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}