use std::io::Read;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};

#[cfg(windows)]
use windows::Win32::System::Threading::CREATE_NO_WINDOW;

use super::session::lock;

const MAX_HELPER_OUTPUT_BYTES: usize = 64 * 1024;

#[derive(Default)]
pub(super) struct HelperOutputReaders {
    pub(super) stdout: Option<JoinHandle<Vec<u8>>>,
    pub(super) stderr: Option<JoinHandle<Vec<u8>>>,
}

pub(super) fn terminate_process_child(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

pub(super) fn configure_mysql_shutdown_process(command: &mut Command) {
    #[cfg(windows)]
    {
        // mysqladmin is a console-subsystem executable. A GUI launcher must
        // explicitly suppress console allocation or Windows briefly creates a
        // visible terminal even though both output streams are captured.
        command.creation_flags(CREATE_NO_WINDOW.0);
    }

    #[cfg(not(windows))]
    let _ = command;
}

pub(super) fn spawn_helper_output_reader<R>(
    name: &str,
    mut reader: R,
) -> std::io::Result<JoinHandle<Vec<u8>>>
where
    R: Read + Send + 'static,
{
    thread::Builder::new()
        .name(name.to_owned())
        .spawn(move || read_bounded_output(&mut reader, MAX_HELPER_OUTPUT_BYTES))
}

fn read_bounded_output(reader: &mut dyn Read, limit: usize) -> Vec<u8> {
    // Continue draining after the diagnostic limit is reached. Discarding the
    // excess prevents both an unbounded allocation and a child blocked on a
    // full stdout or stderr pipe.
    let mut output = Vec::with_capacity(limit.min(4096));
    let mut buffer = [0_u8; 4096];
    loop {
        match reader.read(&mut buffer) {
            Ok(0) | Err(_) => break,
            Ok(length) => {
                let remaining = limit.saturating_sub(output.len());
                output.extend_from_slice(&buffer[..length.min(remaining)]);
            }
        }
    }
    output
}

pub(super) fn join_helper_output_readers(readers: &Arc<Mutex<HelperOutputReaders>>) -> String {
    let (stdout, stderr) = {
        let mut readers = lock(readers);
        (readers.stdout.take(), readers.stderr.take())
    };
    let mut output = stdout
        .and_then(|worker| worker.join().ok())
        .unwrap_or_default();
    let stderr = stderr
        .and_then(|worker| worker.join().ok())
        .unwrap_or_default();
    if !output.is_empty() && !stderr.is_empty() {
        output.push(b'\n');
    }
    output.extend_from_slice(&stderr);
    sanitize_diagnostic_output(&output)
}

fn sanitize_diagnostic_output(output: &[u8]) -> String {
    // Some console tools prefix failures with control characters such as BEL.
    // They have no meaning in a modal and WebView2 renders them as missing-glyph
    // boxes, so retain only controls that contribute to readable formatting.
    String::from_utf8_lossy(output)
        .chars()
        .filter(|character| !character.is_control() || matches!(character, '\n' | '\r' | '\t'))
        .collect::<String>()
        .trim()
        .to_owned()
}

#[cfg(test)]
mod tests {
    use std::io::Cursor;

    use super::*;

    #[test]
    fn bounded_output_is_fully_drained_without_growing_past_limit() {
        let mut source = Cursor::new(vec![b'x'; 32 * 1024]);
        let output = read_bounded_output(&mut source, 1024);

        assert_eq!(output.len(), 1024);
        assert_eq!(source.position(), 32 * 1024);
    }

    #[test]
    fn diagnostics_remove_display_breaking_controls_but_keep_layout() {
        let output =
            sanitize_diagnostic_output(b"\x07mysqladmin failed\r\nerror:\tconnection refused\x00");

        assert_eq!(output, "mysqladmin failed\r\nerror:\tconnection refused");
    }
}
