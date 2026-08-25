mod mysql_helper;
mod session;

use std::collections::BTreeMap;
use std::io::{Read, Write};
use std::path::PathBuf;
use std::process::{Child as ProcessChild, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::Duration;

#[cfg(test)]
use portable_pty::Child as PtyChild;
use portable_pty::{CommandBuilder, native_pty_system};
use tauri::ipc::Channel;

use crate::config::ConfigManager;
use crate::error::{LauncherError, LauncherResult};
use crate::models::{
    BackendEvent, LauncherSnapshot, ServiceId, ServiceSnapshot, ServiceState, SettingsInput,
    SettingsView,
};
use crate::paths::resolve_config_path;
use crate::secrets::decrypt_password;
use crate::service::{
    build_mysql_shutdown_definition, build_service_definition, launch_world_of_warcraft,
};
use mysql_helper::{
    HelperOutputReaders, configure_mysql_shutdown_process, join_helper_output_readers,
    spawn_helper_output_reader, terminate_process_child,
};
use session::{ManagedSession, lock, pty_size, terminate_pty_child};

pub struct LauncherRuntime {
    config: ConfigManager,
    base_dir: PathBuf,
    states: Mutex<BTreeMap<ServiceId, ServiceState>>,
    sessions: Mutex<BTreeMap<ServiceId, ManagedSession>>,
    mysql_shutdown_child: Mutex<Option<Arc<Mutex<ProcessChild>>>>,
    mysql_shutdown_thread: Mutex<Option<JoinHandle<()>>>,
    event_channel: Mutex<Option<Channel<BackendEvent>>>,
    // Lifecycle commands are serialized even though Tauri may dispatch invokes
    // concurrently. This makes duplicate Start/Stop clicks idempotent.
    operation_lock: Mutex<()>,
    shutting_down: AtomicBool,
}

impl LauncherRuntime {
    pub fn new(config: ConfigManager, base_dir: PathBuf) -> Arc<Self> {
        let states = ServiceId::ALL
            .into_iter()
            .map(|service_id| (service_id, ServiceState::Idle))
            .collect();
        Arc::new(Self {
            config,
            base_dir,
            states: Mutex::new(states),
            sessions: Mutex::new(BTreeMap::new()),
            mysql_shutdown_child: Mutex::new(None),
            mysql_shutdown_thread: Mutex::new(None),
            event_channel: Mutex::new(None),
            operation_lock: Mutex::new(()),
            shutting_down: AtomicBool::new(false),
        })
    }

    pub fn initialize(&self, channel: Channel<BackendEvent>) -> LauncherResult<LauncherSnapshot> {
        self.config.ensure_exists()?;
        // Install the channel before taking the snapshot so subsequent state
        // transitions cannot race ahead of the frontend subscription.
        *lock(&self.event_channel) = Some(channel);
        let config = self.config.load_config()?;
        Ok(LauncherSnapshot {
            services: ServiceId::ALL
                .into_iter()
                .map(|service_id| ServiceSnapshot {
                    service_id,
                    state: self.state(service_id),
                })
                .collect(),
            needs_first_run_setup: !config.settings_completed,
        })
    }

    pub fn load_settings(&self) -> LauncherResult<SettingsView> {
        self.config.load_settings()
    }

    pub fn save_settings(&self, settings: SettingsInput) -> LauncherResult<SettingsView> {
        self.config.save_settings(settings)
    }

    pub fn validate_path(&self, value: &str) -> bool {
        let resolved = resolve_config_path(&self.base_dir, value);
        !value.trim().is_empty() && resolved.is_file()
    }

    pub fn start_service(
        self: &Arc<Self>,
        service_id: ServiceId,
        columns: u16,
        rows: u16,
    ) -> LauncherResult<()> {
        let _operation = lock(&self.operation_lock);
        // A request arriving during Starting or Stopping is intentionally a
        // no-op; the in-flight transition remains the single source of truth.
        if self.state(service_id) != ServiceState::Idle {
            return Ok(());
        }
        self.join_previous_session(service_id);
        self.set_state(service_id, ServiceState::Starting);

        let result = self.spawn_service(service_id, columns, rows);
        if let Err(error) = result {
            self.set_state(service_id, ServiceState::Idle);
            return Err(error);
        }
        Ok(())
    }

    fn spawn_service(
        self: &Arc<Self>,
        service_id: ServiceId,
        columns: u16,
        rows: u16,
    ) -> LauncherResult<()> {
        let config = self.config.load_config()?;
        let definition = build_service_definition(service_id, &config, &self.base_dir)?;
        let pair = native_pty_system()
            .openpty(pty_size(columns, rows))
            .map_err(|error| LauncherError::message(format!("Failed to create ConPTY: {error}")))?;

        let mut command = CommandBuilder::new(&definition.program);
        command.args(&definition.arguments);
        if let Some(working_directory) = &definition.working_directory {
            command.cwd(working_directory);
        }

        let child = pair.slave.spawn_command(command).map_err(|error| {
            LauncherError::message(format!("Failed to start {}: {error}", service_id.label()))
        })?;
        let killer = child.clone_killer();
        let child = Arc::new(Mutex::new(child));
        let mut reader = match pair.master.try_clone_reader() {
            Ok(reader) => reader,
            Err(error) => {
                terminate_pty_child(&child);
                return Err(LauncherError::message(format!(
                    "Failed to read {} output: {error}",
                    service_id.label()
                )));
            }
        };
        let writer = match pair.master.take_writer() {
            Ok(writer) => writer,
            Err(error) => {
                terminate_pty_child(&child);
                return Err(LauncherError::message(format!(
                    "Failed to open {} input: {error}",
                    service_id.label()
                )));
            }
        };
        drop(pair.slave);

        // Both workers wait until their handles are registered. A process that
        // exits immediately can therefore never publish Idle before Running.
        let (reader_ready_sender, reader_ready_receiver) = std::sync::mpsc::sync_channel::<()>(0);
        let (waiter_ready_sender, waiter_ready_receiver) = std::sync::mpsc::sync_channel::<()>(0);
        let reader_shutdown = Arc::new(AtomicBool::new(false));
        let reader_runtime = Arc::clone(self);
        let reader_shutdown_worker = Arc::clone(&reader_shutdown);
        let reader_thread = match thread::Builder::new()
            .name(format!("{}-pty-reader", service_id.label().to_lowercase()))
            .spawn(move || {
                let _ = reader_ready_receiver.recv();
                reader_runtime.read_process_output(
                    service_id,
                    &mut reader,
                    &reader_shutdown_worker,
                );
            }) {
            Ok(worker) => worker,
            Err(error) => {
                terminate_pty_child(&child);
                return Err(error.into());
            }
        };

        let waiter_runtime = Arc::clone(self);
        let waiter_child = Arc::clone(&child);
        let waiter_thread = match thread::Builder::new()
            .name(format!(
                "{}-process-waiter",
                service_id.label().to_lowercase()
            ))
            .spawn(move || {
                let _ = waiter_ready_receiver.recv();
                let status = lock(&waiter_child).wait();
                waiter_runtime.process_finished(service_id, status);
            }) {
            Ok(worker) => worker,
            Err(error) => {
                // Releasing this sender lets the already-created reader enter
                // its read loop; closing ConPTY below then unblocks it cleanly.
                reader_shutdown.store(true, Ordering::Release);
                drop(reader_ready_sender);
                terminate_pty_child(&child);
                drop(writer);
                drop(pair.master);
                let _ = reader_thread.join();
                return Err(error.into());
            }
        };

        lock(&self.sessions).insert(
            service_id,
            ManagedSession {
                master: Some(pair.master),
                writer: Some(writer),
                killer,
                reader_shutdown,
                reader_thread: Some(reader_thread),
                waiter_thread: Some(waiter_thread),
            },
        );
        self.set_state(service_id, ServiceState::Running);
        let _ = reader_ready_sender.send(());
        let _ = waiter_ready_sender.send(());
        Ok(())
    }

    pub fn stop_service(self: &Arc<Self>, service_id: ServiceId) -> LauncherResult<()> {
        let _operation = lock(&self.operation_lock);
        if self.state(service_id) != ServiceState::Running {
            return Ok(());
        }
        self.set_state(service_id, ServiceState::Stopping);

        let result = match service_id {
            // Each service receives the graceful stop protocol it understands.
            // Forced application exit uses the kill handles instead.
            ServiceId::Mysql => self.stop_mysql(),
            ServiceId::Worldserver => self.write_raw(service_id, b"server shutdown 1\r\n"),
            ServiceId::Authserver | ServiceId::Ollama => self.write_raw(service_id, b"\x03"),
        };
        if result.is_err() {
            self.set_state(service_id, ServiceState::Running);
        }
        result
    }

    fn stop_mysql(self: &Arc<Self>) -> LauncherResult<()> {
        self.join_mysql_shutdown_thread();
        let config = self.config.load_config()?;
        let password = decrypt_password(&config.sql_password_encrypted)?;
        let shutdown = build_mysql_shutdown_definition(&config, &self.base_dir, password)?;

        let mut command = Command::new(&shutdown.program);
        command
            .args(&shutdown.arguments)
            .current_dir(&shutdown.working_directory)
            // MYSQL_PWD avoids exposing the credential in the process command
            // line, where other local processes could inspect it.
            .env("MYSQL_PWD", shutdown.password)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        configure_mysql_shutdown_process(&mut command);

        let mut child = command.spawn().map_err(|error| {
            LauncherError::message(format!("Failed to run mysqladmin shutdown: {error}"))
        })?;

        let stdout_thread = match child.stdout.take() {
            Some(stdout) => match spawn_helper_output_reader("mysqladmin-stdout", stdout) {
                Ok(worker) => Some(worker),
                Err(error) => {
                    terminate_process_child(&mut child);
                    return Err(error.into());
                }
            },
            None => None,
        };
        let stderr_thread = match child.stderr.take() {
            Some(stderr) => match spawn_helper_output_reader("mysqladmin-stderr", stderr) {
                Ok(worker) => Some(worker),
                Err(error) => {
                    terminate_process_child(&mut child);
                    if let Some(worker) = stdout_thread {
                        let _ = worker.join();
                    }
                    return Err(error.into());
                }
            },
            None => None,
        };
        let output_readers = Arc::new(Mutex::new(HelperOutputReaders {
            stdout: stdout_thread,
            stderr: stderr_thread,
        }));
        let child = Arc::new(Mutex::new(child));
        *lock(&self.mysql_shutdown_child) = Some(Arc::clone(&child));

        let runtime = Arc::clone(self);
        let monitor_child = Arc::clone(&child);
        let monitor_readers = Arc::clone(&output_readers);
        let worker = thread::Builder::new()
            .name("mysqladmin-shutdown".to_owned())
            .spawn(move || runtime.monitor_mysql_shutdown(monitor_child, monitor_readers));
        match worker {
            Ok(worker) => *lock(&self.mysql_shutdown_thread) = Some(worker),
            Err(error) => {
                self.kill_mysql_shutdown_child();
                join_helper_output_readers(&output_readers);
                return Err(error.into());
            }
        }
        Ok(())
    }

    fn monitor_mysql_shutdown(
        self: Arc<Self>,
        child: Arc<Mutex<ProcessChild>>,
        output_readers: Arc<Mutex<HelperOutputReaders>>,
    ) {
        // Polling briefly releases the child lock between checks. Forced exit
        // can therefore acquire the handle and terminate mysqladmin promptly.
        let status = loop {
            match lock(&child).try_wait() {
                Ok(Some(status)) => break Ok(status),
                Ok(None) => thread::sleep(Duration::from_millis(25)),
                Err(error) => break Err(error),
            }
        };

        let details = join_helper_output_readers(&output_readers);
        *lock(&self.mysql_shutdown_child) = None;

        let error = match status {
            Ok(status) if status.success() => return,
            Ok(status) => {
                let code = status.code().unwrap_or(1);
                if details.is_empty() {
                    format!("mysqladmin shutdown failed with code {code}.")
                } else {
                    format!("mysqladmin shutdown failed with code {code}.\n{details}")
                }
            }
            Err(error) => format!("Failed while waiting for mysqladmin shutdown: {error}"),
        };

        let should_report = {
            // Serialize recovery with process-exit finalization so a late
            // helper failure cannot overwrite an already-idle service.
            let _operation = lock(&self.operation_lock);
            if self.shutting_down.load(Ordering::Acquire) {
                false
            } else {
                if self.state(ServiceId::Mysql) == ServiceState::Stopping {
                    self.set_state(ServiceId::Mysql, ServiceState::Running);
                }
                true
            }
        };
        if should_report {
            self.emit_error(Some(ServiceId::Mysql), "MySQL", error);
        }
    }

    pub fn write_service(&self, service_id: ServiceId, text: &str) -> LauncherResult<()> {
        if service_id != ServiceId::Worldserver {
            return Err(LauncherError::message(
                "Interactive commands are only enabled for Worldserver.",
            ));
        }
        if self.state(service_id) != ServiceState::Running {
            return Err(LauncherError::message("Worldserver is not running."));
        }
        let mut command = text.to_owned();
        command.push_str("\r\n");
        self.write_raw(service_id, command.as_bytes())
    }

    pub fn write_terminal_input(&self, service_id: ServiceId, data: &str) -> LauncherResult<()> {
        // xterm emits terminal-protocol replies such as cursor-position reports
        // even with user typing disabled. This bounded path is for those replies,
        // while user-authored commands remain restricted to Worldserver above.
        if data.len() > 4096 {
            return Err(LauncherError::message(
                "Terminal response exceeded the safe input limit.",
            ));
        }
        if self.state(service_id) == ServiceState::Idle {
            return Ok(());
        }
        self.write_raw(service_id, data.as_bytes())
    }

    pub fn resize_service(
        &self,
        service_id: ServiceId,
        columns: u16,
        rows: u16,
    ) -> LauncherResult<()> {
        if let Some(session) = lock(&self.sessions).get(&service_id) {
            if let Some(master) = &session.master {
                master.resize(pty_size(columns, rows)).map_err(|error| {
                    LauncherError::message(format!(
                        "Failed to resize {}: {error}",
                        service_id.label()
                    ))
                })?;
            }
        }
        Ok(())
    }

    pub fn launch_world_of_warcraft(&self) -> LauncherResult<()> {
        let config = self.config.load_config()?;
        launch_world_of_warcraft(&config, &self.base_dir)
    }

    pub fn running_services(&self) -> Vec<ServiceId> {
        ServiceId::SHUTDOWN_ORDER
            .into_iter()
            .filter(|service_id| self.state(*service_id) != ServiceState::Idle)
            .collect()
    }

    pub fn shutdown_all(&self) {
        // Removing sessions under the lifecycle guard prevents a concurrent
        // start, stop, or process-exit callback from taking partial ownership.
        // The guard is released before joins because waiters also use it while
        // completing a natural exit.
        let sessions = {
            let _operation = lock(&self.operation_lock);
            self.shutting_down.store(true, Ordering::Release);
            let mut sessions = lock(&self.sessions);
            std::mem::take(&mut *sessions)
        };

        // Stop the short-lived helper before draining the long-lived PTY
        // sessions it may affect.
        self.kill_mysql_shutdown_child();
        self.join_mysql_shutdown_thread();

        for (service_id, mut session) in sessions {
            session.reader_shutdown.store(true, Ordering::Release);
            let _ = session.killer.kill();
            // Closing both PTY directions unblocks a reader that is waiting for
            // more bytes, allowing its thread to be joined deterministically.
            drop(session.writer.take());
            drop(session.master.take());
            if let Some(reader_thread) = session.reader_thread.take() {
                let _ = reader_thread.join();
            }
            if let Some(waiter_thread) = session.waiter_thread.take() {
                let _ = waiter_thread.join();
            }
            self.set_state(service_id, ServiceState::Idle);
        }
    }

    fn kill_mysql_shutdown_child(&self) {
        if let Some(child) = lock(&self.mysql_shutdown_child).take() {
            let mut child = lock(&child);
            let _ = child.kill();
            let _ = child.wait();
        }
    }

    fn join_mysql_shutdown_thread(&self) {
        if let Some(worker) = lock(&self.mysql_shutdown_thread).take() {
            let _ = worker.join();
        }
    }

    fn read_process_output(
        &self,
        service_id: ServiceId,
        reader: &mut dyn Read,
        reader_shutdown: &AtomicBool,
    ) {
        // Forward natural read chunks without parsing ANSI. xterm owns escape
        // sequence interpretation, cursor state, and scrollback behavior.
        let mut buffer = [0_u8; 8192];
        loop {
            match reader.read(&mut buffer) {
                Ok(0) => break,
                Ok(length) => {
                    self.emit(BackendEvent::Output {
                        service_id,
                        text: String::from_utf8_lossy(&buffer[..length]).into_owned(),
                    });
                }
                Err(error) => {
                    if !reader_shutdown.load(Ordering::Acquire)
                        && self.state(service_id) != ServiceState::Stopping
                    {
                        self.emit_error(
                            Some(service_id),
                            service_id.label(),
                            format!("Terminal output stopped unexpectedly: {error}"),
                        );
                    }
                    break;
                }
            }
        }
    }

    fn process_finished(
        &self,
        service_id: ServiceId,
        status: std::io::Result<portable_pty::ExitStatus>,
    ) {
        // Start, stop, and exit transitions share one guard so an I/O failure
        // from a process that just exited cannot restore a stale Running state.
        let _operation = lock(&self.operation_lock);
        let cleanup = {
            let mut sessions = lock(&self.sessions);
            let Some(session) = sessions.get_mut(&service_id) else {
                // Forced shutdown takes ownership of the whole session map and
                // performs the same cleanup before joining this waiter.
                return;
            };
            session.reader_shutdown.store(true, Ordering::Release);
            (
                session.writer.take(),
                session.master.take(),
                session.reader_thread.take(),
            )
        };

        // Closing ConPTY after the process handle signals exit guarantees the
        // synchronous reader reaches EOF; waiting for EOF first can deadlock.
        drop(cleanup.0);
        drop(cleanup.1);
        if let Some(reader_thread) = cleanup.2 {
            let _ = reader_thread.join();
        }

        if let Err(error) = status
            && !self.shutting_down.load(Ordering::Acquire)
        {
            self.emit_error(
                Some(service_id),
                service_id.label(),
                format!("Failed while waiting for process exit: {error}"),
            );
        }
        self.set_state(service_id, ServiceState::Idle);
    }

    fn join_previous_session(&self, service_id: ServiceId) {
        let previous = lock(&self.sessions).remove(&service_id);
        if let Some(mut session) = previous {
            session.reader_shutdown.store(true, Ordering::Release);
            drop(session.writer.take());
            drop(session.master.take());
            if let Some(reader_thread) = session.reader_thread.take() {
                let _ = reader_thread.join();
            }
            if let Some(waiter_thread) = session.waiter_thread.take() {
                let _ = waiter_thread.join();
            }
        }
    }

    fn write_raw(&self, service_id: ServiceId, bytes: &[u8]) -> LauncherResult<()> {
        let mut sessions = lock(&self.sessions);
        let session = sessions.get_mut(&service_id).ok_or_else(|| {
            LauncherError::message(format!("{} process is unavailable.", service_id.label()))
        })?;
        let writer = session.writer.as_mut().ok_or_else(|| {
            LauncherError::message(format!("{} process is unavailable.", service_id.label()))
        })?;
        writer.write_all(bytes)?;
        writer.flush()?;
        Ok(())
    }

    fn state(&self, service_id: ServiceId) -> ServiceState {
        lock(&self.states)
            .get(&service_id)
            .copied()
            .unwrap_or(ServiceState::Idle)
    }

    fn set_state(&self, service_id: ServiceId, state: ServiceState) {
        lock(&self.states).insert(service_id, state);
        self.emit(BackendEvent::StateChanged { service_id, state });
    }

    fn emit_error(
        &self,
        service_id: Option<ServiceId>,
        title: impl Into<String>,
        message: impl Into<String>,
    ) {
        self.emit(BackendEvent::Error {
            service_id,
            title: title.into(),
            message: message.into(),
        });
    }

    fn emit(&self, event: BackendEvent) {
        let mut channel = lock(&self.event_channel);
        // A failed send means the webview subscription is gone. Dropping the
        // stale sink avoids paying for repeated failed sends from reader threads.
        if channel
            .as_ref()
            .is_some_and(|sink| sink.send(event).is_err())
        {
            *channel = None;
        }
    }
}

#[cfg(test)]
mod tests {
    use std::time::{Duration, Instant};

    use tauri::ipc::InvokeResponseBody;
    #[cfg(windows)]
    use windows::Win32::System::Console::GetConsoleWindow;

    use super::*;

    #[test]
    fn service_order_stops_worldserver_before_mysql() {
        assert_eq!(ServiceId::SHUTDOWN_ORDER[0], ServiceId::Worldserver);
        assert_eq!(ServiceId::SHUTDOWN_ORDER[2], ServiceId::Mysql);
    }

    #[test]
    fn initialization_snapshot_preserves_first_run_status() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let config = ConfigManager::new(directory.path().join("config.json"));
        config
            .save_settings(SettingsInput {
                sql_host: "127.0.0.1".to_owned(),
                sql_port: 3306,
                sql_user: "acore".to_owned(),
                sql_password: String::new(),
                client_path: String::new(),
                mysql_path: String::new(),
                auth_server_path: String::new(),
                world_server_path: String::new(),
            })
            .expect("save fixture settings");
        let runtime = LauncherRuntime::new(config, directory.path().to_path_buf());
        let channel = Channel::<BackendEvent>::new(|_| Ok(()));

        let snapshot = runtime.initialize(channel).expect("initialize runtime");

        assert!(!snapshot.needs_first_run_setup);
    }

    #[test]
    fn executable_validation_exposes_only_file_existence() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let executable = directory.path().join("fixture.exe");
        std::fs::write(&executable, []).expect("create executable fixture");
        let runtime = LauncherRuntime::new(
            ConfigManager::new(directory.path().join("config.json")),
            directory.path().to_path_buf(),
        );

        assert!(runtime.validate_path("fixture.exe"));
        assert!(!runtime.validate_path("missing.exe"));
        assert!(!runtime.validate_path("  "));
    }

    #[cfg(windows)]
    #[test]
    fn mysql_shutdown_console_probe() {
        const CHILD_PROBE: &str = "AZEROTHCORE_MYSQLADMIN_CONSOLE_PROBE";

        if std::env::var_os(CHILD_PROBE).is_some() {
            // The same test executable is re-entered as a console-subsystem
            // child, allowing the test to observe CREATE_NO_WINDOW directly.
            let console = unsafe { GetConsoleWindow() };
            assert!(
                console.0.is_null(),
                "hidden helper process unexpectedly owns a console window"
            );
            return;
        }

        let mut command = Command::new(std::env::current_exe().expect("test executable"));
        command
            .arg("mysql_shutdown_console_probe")
            .arg("--nocapture")
            .env(CHILD_PROBE, "1")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        configure_mysql_shutdown_process(&mut command);

        let output = command.output().expect("start hidden console probe");
        assert!(
            output.status.success(),
            "hidden console probe failed:\n{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    #[test]
    fn partial_setup_cleanup_terminates_the_spawned_child() {
        let command_processor = std::env::var_os("COMSPEC").expect("command processor");
        let child = Command::new(command_processor)
            .args(["/D", "/Q", "/C", "ping -n 30 127.0.0.1 >nul"])
            .spawn()
            .expect("spawn cleanup fixture");
        let child: Box<dyn PtyChild + Send + Sync> = Box::new(child);
        let child = Arc::new(Mutex::new(child));

        terminate_pty_child(&child);

        assert!(
            lock(&child)
                .try_wait()
                .expect("query fixture status")
                .is_some(),
            "partial setup cleanup left its child running"
        );
    }

    #[test]
    fn reader_thread_forwards_output_through_tauri_channel() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let config = ConfigManager::new(directory.path().join("config.json"));
        config
            .save_settings(SettingsInput {
                sql_host: "127.0.0.1".to_owned(),
                sql_port: 3306,
                sql_user: "acore".to_owned(),
                sql_password: String::new(),
                client_path: String::new(),
                mysql_path: String::new(),
                auth_server_path: std::env::var("COMSPEC").expect("command processor"),
                world_server_path: String::new(),
            })
            .expect("save fixture settings");
        let runtime = LauncherRuntime::new(config, directory.path().to_path_buf());

        let (sender, receiver) = std::sync::mpsc::channel::<String>();
        let channel = Channel::<BackendEvent>::new(move |body| {
            if let InvokeResponseBody::Json(json) = body {
                let _ = sender.send(json);
            }
            Ok(())
        });
        *lock(&runtime.event_channel) = Some(channel);

        runtime
            .start_service(ServiceId::Authserver, 80, 24)
            .expect("start command processor fixture");
        runtime
            .write_raw(
                ServiceId::Authserver,
                b"\x1b[1;1Recho runtime-channel-marker\r",
            )
            .expect("write fixture command");

        let deadline = Instant::now() + Duration::from_secs(5);
        let mut events = String::new();
        while Instant::now() < deadline && !events.contains("runtime-channel-marker") {
            if let Ok(event) = receiver.recv_timeout(Duration::from_millis(100)) {
                events.push_str(&event);
            }
        }
        runtime.shutdown_all();

        assert!(
            events.contains("runtime-channel-marker"),
            "runtime channel did not receive PTY output: {events}"
        );
    }

    #[test]
    fn exited_process_leaves_stopping_and_can_restart() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let config = ConfigManager::new(directory.path().join("config.json"));
        config
            .save_settings(SettingsInput {
                sql_host: "127.0.0.1".to_owned(),
                sql_port: 3306,
                sql_user: "acore".to_owned(),
                sql_password: String::new(),
                client_path: String::new(),
                mysql_path: String::new(),
                auth_server_path: std::env::var("COMSPEC").expect("command processor"),
                world_server_path: String::new(),
            })
            .expect("save fixture settings");
        let runtime = LauncherRuntime::new(config, directory.path().to_path_buf());

        for cycle in 1..=3 {
            runtime
                .start_service(ServiceId::Authserver, 80, 24)
                .expect("start command processor fixture");
            runtime
                .write_raw(ServiceId::Authserver, b"\x1b[1;1R")
                .expect("answer cursor query");
            runtime
                .stop_service(ServiceId::Authserver)
                .expect("enter stopping state");
            runtime
                .write_raw(ServiceId::Authserver, b"exit\r")
                .expect("exit fixture process");

            let deadline = Instant::now() + Duration::from_secs(5);
            while runtime.state(ServiceId::Authserver) != ServiceState::Idle
                && Instant::now() < deadline
            {
                thread::sleep(Duration::from_millis(25));
            }
            assert_eq!(
                runtime.state(ServiceId::Authserver),
                ServiceState::Idle,
                "fixture remained in Stopping during cycle {cycle}"
            );
        }
        runtime.shutdown_all();
        assert!(lock(&runtime.sessions).is_empty());
    }
}
