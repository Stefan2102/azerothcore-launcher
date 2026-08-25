import { AlertTriangle } from "lucide-react";
import { Modal } from "./Modal";

interface AlertDialogProps {
  title: string;
  message: string;
  onClose: () => void;
}

export function AlertDialog({ title, message, onClose }: AlertDialogProps) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="alert-content">
        <AlertTriangle aria-hidden="true" size={28} />
        <p>{message}</p>
      </div>
      <footer className="modal__actions">
        <button
          className="control-button button button--primary"
          onClick={onClose}
          type="button"
        >
          OK
        </button>
      </footer>
    </Modal>
  );
}
