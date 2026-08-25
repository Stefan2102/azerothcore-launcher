use std::io::Write;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex, MutexGuard};
use std::thread::JoinHandle;

use portable_pty::{Child as PtyChild, ChildKiller, MasterPty, PtySize};

const MIN_COLUMNS: u16 = 20;
const MIN_ROWS: u16 = 5;

pub(super) struct ManagedSession {
    // Optional I/O handles allow the process waiter to close ConPTY and join
    // the reader as soon as the child exits, while retaining the waiter handle
    // for deterministic collection before restart or application shutdown.
    pub(super) master: Option<Box<dyn MasterPty + Send>>,
    pub(super) writer: Option<Box<dyn Write + Send>>,
    pub(super) killer: Box<dyn ChildKiller + Send + Sync>,
    pub(super) reader_shutdown: Arc<AtomicBool>,
    pub(super) reader_thread: Option<JoinHandle<()>>,
    pub(super) waiter_thread: Option<JoinHandle<()>>,
}

pub(super) fn pty_size(columns: u16, rows: u16) -> PtySize {
    // ConPTY behaves poorly with zero-sized dimensions during initial layout,
    // so startup and resize requests are clamped to a usable terminal.
    PtySize {
        rows: rows.max(MIN_ROWS),
        cols: columns.max(MIN_COLUMNS),
        pixel_width: 0,
        pixel_height: 0,
    }
}

pub(super) fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    // A previous panic must not make process cleanup impossible. The protected
    // values remain structurally valid, so recovery is safer than cascading.
    mutex
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

pub(super) fn terminate_pty_child(child: &Arc<Mutex<Box<dyn PtyChild + Send + Sync>>>) {
    // Setup failures occur after CreateProcess has succeeded but before the
    // session can be registered. Explicit termination prevents an unmanaged
    // service from surviving a failed reader, writer, or worker allocation.
    let mut child = lock(child);
    let _ = child.kill();
    let _ = child.wait();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn terminal_size_enforces_safe_minimums() {
        let size = pty_size(1, 2);
        assert_eq!(size.cols, MIN_COLUMNS);
        assert_eq!(size.rows, MIN_ROWS);
    }
}
