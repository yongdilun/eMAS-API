const CancelConfirmModal = ({ open, onClose, onConfirm, busy }) => {
  if (!open) return null

  return (
    <div className="absolute inset-0 z-20 bg-black/30 flex items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-lg">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Cancel current session?</h3>
        <p className="mt-2 text-xs text-gray-600 dark:text-gray-300">
          Completed steps are not rolled back. Pending steps will be skipped.
        </p>
        <div className="mt-4 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 disabled:opacity-60"
          >
            Keep Running
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
          >
            Confirm Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

export default CancelConfirmModal

