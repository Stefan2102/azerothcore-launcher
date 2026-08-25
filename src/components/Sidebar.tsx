import {
  Database,
  Globe2,
  Power,
  Settings,
  Shield,
  Sparkles,
  Sword,
} from "lucide-react";
import logo from "../assets/logo.png";
import {
  actionLabel,
  serviceOrder,
  type ServiceId,
  type ServiceState,
} from "../types/launcher";

interface SidebarProps {
  states: Record<ServiceId, ServiceState>;
  onServiceAction: (serviceId: ServiceId) => void;
  onLaunchWow: () => void;
  onOpenSettings: () => void;
  onExit: () => void;
}

const serviceIcons = {
  mysql: Database,
  authserver: Shield,
  worldserver: Globe2,
  ollama: Sparkles,
} satisfies Record<ServiceId, typeof Database>;

export function Sidebar({
  states,
  onServiceAction,
  onLaunchWow,
  onOpenSettings,
  onExit,
}: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Launcher controls">
      <div className="brand">
        <img
          src={logo}
          className="brand__logo"
          alt="AzerothCore"
          draggable={false}
        />
        <div className="brand__title">AzerothCore</div>
        <div className="brand__subtitle">Launcher</div>
      </div>

      <nav className="sidebar__actions" aria-label="Services">
        {serviceOrder.map((serviceId) => {
          const Icon = serviceIcons[serviceId];
          const state = states[serviceId];
          return (
            <button
              className="control-button side-button"
              data-running={state === "running"}
              data-transitioning={state === "starting" || state === "stopping"}
              disabled={state === "starting" || state === "stopping"}
              key={serviceId}
              onClick={() => onServiceAction(serviceId)}
              type="button"
            >
              <Icon aria-hidden="true" size={22} strokeWidth={1.8} />
              <span>{actionLabel(serviceId, state)}</span>
            </button>
          );
        })}

        <button
          className="control-button side-button"
          onClick={onLaunchWow}
          type="button"
        >
          <Sword aria-hidden="true" size={22} strokeWidth={1.8} />
          <span>Launch World of Warcraft</span>
        </button>
      </nav>

      <div className="sidebar__footer">
        <button
          className="control-button side-button"
          onPointerDown={(event) => event.preventDefault()}
          onClick={onOpenSettings}
          type="button"
        >
          <Settings aria-hidden="true" size={22} strokeWidth={1.8} />
          <span>Settings</span>
        </button>
        <button
          className="control-button side-button side-button--danger"
          onClick={onExit}
          type="button"
        >
          <Power aria-hidden="true" size={22} strokeWidth={1.8} />
          <span>Exit</span>
        </button>
      </div>
    </aside>
  );
}
