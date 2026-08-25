#![cfg(windows)]

use std::io::{Read, Write};
use std::time::{Duration, Instant};

use portable_pty::{CommandBuilder, PtySize, native_pty_system};

#[test]
fn conpty_preserves_ansi_output_stdin_resize_and_cleanup() {
    let pair = native_pty_system()
        .openpty(PtySize {
            rows: 12,
            cols: 60,
            pixel_width: 0,
            pixel_height: 0,
        })
        .expect("create ConPTY");
    pair.master
        .resize(PtySize {
            rows: 20,
            cols: 100,
            pixel_width: 0,
            pixel_height: 0,
        })
        .expect("resize ConPTY");

    let command_processor = std::env::var_os("COMSPEC").expect("Windows command processor");
    let mut command = CommandBuilder::new(command_processor);
    command.args(["/D", "/Q", "/V:ON", "/K"]);
    let mut child = pair.slave.spawn_command(command).expect("spawn fixture");
    let mut reader = pair.master.try_clone_reader().expect("clone reader");
    let mut writer = pair.master.take_writer().expect("take writer");
    drop(pair.slave);

    // ConPTY uses synchronous pipes. Output must be drained concurrently or a
    // child can block before it reaches commands written to its input stream.
    let (output_sender, output_receiver) = std::sync::mpsc::channel::<String>();
    let reader_thread = std::thread::spawn(move || {
        let mut buffer = [0_u8; 4096];
        while let Ok(length) = reader.read(&mut buffer) {
            if length == 0 {
                break;
            }
            if output_sender
                .send(String::from_utf8_lossy(&buffer[..length]).into_owned())
                .is_err()
            {
                break;
            }
        }
    });

    writer
        .write_all(b"echo \x1b[31mready\x1b[0m\rset input=hello launcher\recho echo:!input!\r")
        .expect("write fixture commands");
    writer.flush().expect("flush fixture commands");

    let deadline = Instant::now() + Duration::from_secs(5);
    let mut output = String::new();
    while Instant::now() < deadline && !output.contains("echo:hello launcher") {
        if let Ok(chunk) = output_receiver.recv_timeout(Duration::from_millis(100)) {
            output.push_str(&chunk);
            if chunk.contains("\u{1b}[6n") {
                writer
                    .write_all(b"\x1b[1;1R")
                    .expect("answer ConPTY cursor query");
                writer.flush().expect("flush cursor response");
            }
        }
    }

    child.kill().expect("terminate fixture");
    let status = child.wait().expect("wait for terminated fixture");
    drop(writer);
    drop(pair.master);
    reader_thread.join().expect("join ConPTY reader");

    assert!(!status.success(), "fixture should have been terminated");
    assert!(
        output.contains("\u{1b}[?9001h") && output.contains("ready"),
        "missing ANSI output in {output:?}"
    );
    assert!(
        output.contains("echo:hello launcher"),
        "missing stdin echo in {output:?}"
    );
}
