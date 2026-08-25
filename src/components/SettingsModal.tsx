import { useEffect, useId, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { Eye, EyeOff, FolderOpen } from "lucide-react";
import { errorMessage, launcherBackend } from "../lib/backend";
import {
  executableFields,
  fieldError,
  type ExecutableField,
} from "../lib/settings";
import type { SettingsInput, SettingsView } from "../types/launcher";
import { Modal } from "./Modal";

interface SettingsModalProps {
  onCancel: () => void;
  onError: (title: string, message: string) => void;
  onSaved: (settings: SettingsView) => void;
}

type PathErrors = Partial<Record<ExecutableField, string>>;

const pathMetadata: Record<
  ExecutableField,
  { label: string; dialogTitle: string; missing: string }
> = {
  clientPath: {
    label: "Client Path",
    dialogTitle: "World of Warcraft executable",
    missing: "Executable not found at this path.",
  },
  mysqlPath: {
    label: "MySQL (mysqld.exe)",
    dialogTitle: "mysqld.exe",
    missing: "mysqld.exe not found at this path.",
  },
  authServerPath: {
    label: "Authserver (authserver.exe)",
    dialogTitle: "authserver.exe",
    missing: "authserver.exe not found at this path.",
  },
  worldServerPath: {
    label: "Worldserver (worldserver.exe)",
    dialogTitle: "worldserver.exe",
    missing: "worldserver.exe not found at this path.",
  },
};

export function SettingsModal({
  onCancel,
  onError,
  onSaved,
}: SettingsModalProps) {
  const [settings, setSettings] = useState<SettingsInput | null>(null);
  const [pathErrors, setPathErrors] = useState<PathErrors>({});
  const [saving, setSaving] = useState(false);
  const validationVersions = useRef<Record<ExecutableField, number>>({
    clientPath: 0,
    mysqlPath: 0,
    authServerPath: 0,
    worldServerPath: 0,
  });

  useEffect(() => {
    // Native settings loading may finish after the user closes the modal. Avoid
    // scheduling state updates against a component that no longer owns the data.
    let active = true;
    void launcherBackend
      .loadSettings()
      .then((loaded) => {
        if (active) {
          setSettings({
            sqlHost: loaded.sqlHost,
            sqlPort: loaded.sqlPort,
            sqlUser: loaded.sqlUser,
            sqlPassword: loaded.sqlPassword,
            clientPath: loaded.clientPath,
            mysqlPath: loaded.mysqlPath,
            authServerPath: loaded.authServerPath,
            worldServerPath: loaded.worldServerPath,
          });
        }
      })
      .catch((error) => {
        if (active) {
          onCancel();
          onError("Settings", errorMessage(error));
        }
      });
    return () => {
      active = false;
    };
  }, [onCancel, onError]);

  function update<K extends keyof SettingsInput>(key: K, value: SettingsInput[K]) {
    setSettings((current) =>
      current ? { ...current, [key]: value } : current,
    );
    if (executableFields.includes(key as ExecutableField)) {
      validationVersions.current[key as ExecutableField] += 1;
      // A missing-path warning describes the previous value and becomes stale as
      // soon as the user edits that field.
      setPathErrors((current) => ({ ...current, [key]: "" }));
    }
  }

  async function validatePath(
    field: ExecutableField,
    value = settings?.[field] ?? "",
  ) {
    const version = validationVersions.current[field] + 1;
    validationVersions.current[field] = version;
    if (!value.trim()) {
      setPathErrors((current) => ({ ...current, [field]: "" }));
      return;
    }
    try {
      // Rust performs resolution so validation follows the same development or
      // release base-directory rules used when services actually start.
      const exists = await launcherBackend.validateExecutablePath(value);
      if (validationVersions.current[field] !== version) return;
      setPathErrors((current) => ({
        ...current,
        [field]: exists ? "" : pathMetadata[field].missing,
      }));
    } catch (error) {
      if (validationVersions.current[field] !== version) return;
      onError("Path validation", errorMessage(error));
    }
  }

  async function browse(field: ExecutableField) {
    try {
      const selected = await open({
        title: pathMetadata[field].dialogTitle,
        multiple: false,
        directory: false,
        filters: [{ name: "Executables", extensions: ["exe"] }],
      });
      if (typeof selected === "string") {
        update(field, selected);
        await validatePath(field, selected);
      }
    } catch (error) {
      onError("Executable picker", errorMessage(error));
    }
  }

  async function save() {
    setSaving(true);
    try {
      if (!settings) return;
      const saved = await launcherBackend.saveSettings(settings);
      onSaved(saved);
    } catch (error) {
      onError("Settings", errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Launcher Settings" onClose={onCancel} wide>
      {!settings ? (
        <div className="settings-loading">Loading settings…</div>
      ) : (
        <form
          className="settings-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <SettingsSection
            description="Connection details used for the MySQL shutdown helper."
            title="Database"
          >
            <TextField
              error={fieldError("sqlHost", settings.sqlHost)}
              label="SQL Server IP"
              onChange={(value) => update("sqlHost", value)}
              placeholder="127.0.0.1"
              value={settings.sqlHost}
            />
            <label className="settings-field">
              <span>SQL Server Port</span>
              <input
                max={65535}
                min={1}
                onChange={(event) => update("sqlPort", Number(event.target.value))}
                type="number"
                value={settings.sqlPort}
              />
              <small>{fieldError("sqlPort", settings.sqlPort)}</small>
            </label>
            <TextField
              error={fieldError("sqlUser", settings.sqlUser)}
              label="SQL Server User"
              onChange={(value) => update("sqlUser", value)}
              placeholder="acore"
              value={settings.sqlUser}
            />
            <TextField
              label="SQL Server Password"
              onChange={(value) => update("sqlPassword", value)}
              placeholder="acore"
              revealable
              type="password"
              value={settings.sqlPassword}
            />
          </SettingsSection>

          <SettingsSection
            description="Choose the World of Warcraft executable launched from the sidebar."
            title="World of Warcraft client"
          >
            <PathField
              field="clientPath"
              onBlur={() => void validatePath("clientPath")}
              onBrowse={() => void browse("clientPath")}
              onChange={(value) => update("clientPath", value)}
              error={pathErrors.clientPath}
              value={settings.clientPath}
            />
          </SettingsSection>

          <SettingsSection
            className="settings-section--paths"
            description="Select the local executables the launcher manages."
            title="Server executables"
          >
            {(["mysqlPath", "authServerPath", "worldServerPath"] as const).map(
              (field) => (
                <PathField
                  error={pathErrors[field]}
                  field={field}
                  key={field}
                  onBlur={() => void validatePath(field)}
                  onBrowse={() => void browse(field)}
                  onChange={(value) => update(field, value)}
                  value={settings[field]}
                />
              ),
            )}
          </SettingsSection>

          <footer className="modal__actions settings-form__actions">
            <button
              className="control-button button button--secondary"
              onClick={onCancel}
              type="button"
            >
              Cancel
            </button>
            <button
              className="control-button button button--primary"
              disabled={saving}
              type="submit"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </footer>
        </form>
      )}
    </Modal>
  );
}

interface SettingsSectionProps {
  children: React.ReactNode;
  className?: string;
  description: string;
  title: string;
}

function SettingsSection({
  children,
  className = "",
  description,
  title,
}: SettingsSectionProps) {
  const headingId = useId();

  return (
    <section aria-labelledby={headingId} className={`settings-section ${className}`.trim()}>
      <header className="settings-section__header">
        <h3 id={headingId}>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="settings-section__fields">{children}</div>
    </section>
  );
}

interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  type?: "text" | "password";
  revealable?: boolean;
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  error = "",
  type = "text",
  revealable = false,
}: TextFieldProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const inputType = revealable && passwordVisible ? "text" : type;

  return (
    <label className="settings-field">
      <span>{label}</span>
      {revealable ? (
        <span className="settings-field__input-action">
          <input
            onChange={(event) => onChange(event.target.value)}
            placeholder={placeholder}
            type={inputType}
            value={value}
          />
          <button
            aria-label={passwordVisible ? "Hide SQL Server Password" : "Show SQL Server Password"}
            aria-pressed={passwordVisible}
            className="control-button settings-password-toggle"
            onClick={() => setPasswordVisible((current) => !current)}
            type="button"
          >
            {passwordVisible ? (
              <EyeOff aria-hidden="true" size={16} />
            ) : (
              <Eye aria-hidden="true" size={16} />
            )}
          </button>
        </span>
      ) : (
        <input
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          type={inputType}
          value={value}
        />
      )}
      <small>{error}</small>
    </label>
  );
}

interface PathFieldProps {
  field: ExecutableField;
  value: string;
  error?: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  onBrowse: () => void;
}

function PathField({
  field,
  value,
  error = "",
  onChange,
  onBlur,
  onBrowse,
}: PathFieldProps) {
  return (
    <label className="settings-field settings-field--path">
      <span>{pathMetadata[field].label}</span>
      <span className="settings-field__path-row">
        <input
          onBlur={onBlur}
          onChange={(event) => onChange(event.target.value)}
          value={value}
        />
        <button
          className="control-button browse-button"
          onClick={onBrowse}
          type="button"
        >
          <FolderOpen aria-hidden="true" size={17} />
          Browse…
        </button>
      </span>
      <small>{error}</small>
    </label>
  );
}
