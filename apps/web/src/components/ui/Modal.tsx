import type { PropsWithChildren, ReactNode } from "react";
import { Button } from "./Button";

type ModalProps = PropsWithChildren<{
  title: string;
  isOpen: boolean;
  onClose: () => void;
  footer?: ReactNode;
}>;

export function Modal({ title, isOpen, onClose, footer, children }: ModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-md border border-border bg-surface p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text">{title}</h3>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="space-y-4">{children}</div>
        {footer ? <div className="mt-5 flex items-center justify-end gap-2">{footer}</div> : null}
      </div>
    </div>
  );
}
