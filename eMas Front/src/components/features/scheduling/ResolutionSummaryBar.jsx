const ResolutionSummaryBar = ({
  selectedCount = 0,
  loading = false,
  onApplyReplan,
}) => {
  const applyDisabled = loading || selectedCount === 0

  return (
    <div className="sticky bottom-0 border-t border-hairline bg-surface-1/95 backdrop-blur p-3 mt-3">
      <div className="flex flex-wrap gap-2 items-center">
        <button
          type="button"
          onClick={onApplyReplan}
          disabled={applyDisabled}
          className="h-9 px-4 rounded-md bg-primary text-white text-sm font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Running…' : 'Apply and Replan'}
        </button>
      </div>
    </div>
  )
}

export default ResolutionSummaryBar
