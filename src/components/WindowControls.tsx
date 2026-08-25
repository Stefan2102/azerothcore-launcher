import { Minus, X } from "lucide-react";

interface WindowControlsProps {
  onClose: () => void;
  onMinimize: () => void;
}

export function WindowControls({
  onClose,
  onMinimize,
}: WindowControlsProps) {
  return (
    <div className="window-controls" role="group" aria-label="Window controls">
      <button
        aria-label="Minimize window"
        className="control-button window-control"
        onClick={onMinimize}
        type="button"
      >
        <Minus aria-hidden="true" size={16} strokeWidth={1.7} />
      </button>
      <button
        aria-label="Close window"
        className="control-button window-control window-control--close"
        onClick={onClose}
        type="button"
      >
        <X aria-hidden="true" size={17} strokeWidth={1.7} />
      </button>
    </div>
  );
}
