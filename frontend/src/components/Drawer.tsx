/**
 * Right-side detail drawer for master/detail workspaces.
 *
 * Opens on row activation, closes on Escape / overlay click / close button.
 * Focus moves to the close button on open and returns to the invoking
 * element on close so keyboard flows stay intact.
 */

import { useEffect, useRef } from "react"
import { X } from "lucide-react"

export default function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
}) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return
    returnFocusRef.current = document.activeElement as HTMLElement | null
    closeButtonRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    document.addEventListener("keydown", handleKeyDown)
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = ""
      returnFocusRef.current?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="drawer-root" role="presentation">
      <div className="drawer-overlay" onClick={onClose} aria-hidden />
      <aside
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="drawer-head">
          <div className="drawer-head-text">
            <h3>{title}</h3>
            {subtitle && <span>{subtitle}</span>}
          </div>
          <button
            type="button"
            ref={closeButtonRef}
            className="drawer-close"
            onClick={onClose}
            aria-label="Close details"
          >
            <X size={16} />
          </button>
        </header>
        <div className="drawer-body">{children}</div>
        {footer && <footer className="drawer-footer">{footer}</footer>}
      </aside>
    </div>
  )
}
