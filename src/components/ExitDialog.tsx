import { AlertTriangle } from "lucide-react";
import { serviceLabels, type ServiceId } from "../types/launcher";
import { Modal } from "./Modal";

interface ExitDialogProps {
  services: ServiceId[];
  onCancel: () => void;
  onConfirm: () => void;
}

export function ExitDialog({ services, onCancel, onConfirm }: ExitDialogProps) {
  return (
    <Modal title="Services still running" onClose={onCancel}>
      <div className="alert-content alert-content--warning">
        <AlertTriangle aria-hidden="true" size={30} />
        <div>
          <p>
            Some services are still running and should be shut down before you
            close the launcher.
          </p>
          <ul>
            {services.map((serviceId) => (
              <li key={serviceId}>{serviceLabels[serviceId]}</li>
            ))}
          </ul>
        </div>
      </div>
      <footer className="modal__actions">
        <button
          className="control-button button button--secondary"
          onClick={onCancel}
          type="button"
        >
          Cancel
        </button>
        <button
          className="control-button button button--danger"
          onClick={onConfirm}
          type="button"
        >
          Exit anyway
        </button>
      </footer>
    </Modal>
  );
}
