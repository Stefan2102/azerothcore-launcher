use std::fmt::{Display, Formatter};

#[derive(Debug)]
pub struct LauncherError(pub String);

impl LauncherError {
    pub fn message(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

impl Display for LauncherError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for LauncherError {}

impl From<std::io::Error> for LauncherError {
    fn from(error: std::io::Error) -> Self {
        Self(error.to_string())
    }
}

impl From<serde_json::Error> for LauncherError {
    fn from(error: serde_json::Error) -> Self {
        Self(error.to_string())
    }
}

pub type LauncherResult<T> = Result<T, LauncherError>;
