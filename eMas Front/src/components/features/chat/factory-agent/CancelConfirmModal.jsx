const CancelConfirmModal = ({ open, onClose, onConfirm, busy }) => {
 if (!open) return null

 return (
 <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/30 p-4">
 <div className="w-full max-w-sm rounded-lg border border-hairline bg-surface-1 p-4">
 <h3 className="text-sm font-semibold text-ink">Cancel current session?</h3>
 <p className="mt-2 text-xs text-ink-subtle">
 Completed steps are not rolled back. Pending steps will be skipped.
 </p>
 <div className="mt-4 flex items-center justify-end gap-2">
 <button
 type="button"
 onClick={onClose}
 disabled={busy}
 className="px-3 py-1.5 rounded-md text-xs font-semibold bg-surface-2 text-ink hover:bg-surface-3 disabled:opacity-60"
 >
 Keep Running
 </button>
 <button
 type="button"
 onClick={onConfirm}
 disabled={busy}
 className="px-3 py-1.5 rounded-md text-xs font-semibold bg-inverse-canvas text-inverse-ink hover:opacity-90 disabled:opacity-60"
 >
 Confirm Cancel
 </button>
 </div>
 </div>
 </div>
 )
}

export default CancelConfirmModal
