import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  children: ReactNode;
  onClose?: () => void;
  title: string;
  wide?: boolean;
}

export function Modal({ children, onClose, title, wide = false }: ModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;

    const previousFocus = document.activeElement;
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      // jsdom and older embedded engines can still render the accessible
      // fallback while production WebView2 owns modal stacking and focus.
      dialog.setAttribute("open", "");
    }

    return () => {
      if (dialog.open && typeof dialog.close === "function") dialog.close();
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
        previousFocus.focus();
      }
    };
  }, []);

  return (
    <dialog
      aria-labelledby={titleId}
      className={`modal ${wide ? "modal--wide" : ""}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose?.();
      }}
      ref={dialogRef}
    >
      <header className="modal__header">
        <h2 id={titleId}>{title}</h2>
        {onClose && (
          <button
            aria-label="Close dialog"
            className="control-button icon-button"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={20} />
          </button>
        )}
      </header>
      {children}
    </dialog>
  );
}
