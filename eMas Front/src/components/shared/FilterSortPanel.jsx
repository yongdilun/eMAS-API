/**
 * FilterSortPanel — reusable slide-out multi-filter + sort panel.
 * UC-FS01..FS04: combine machine, status, priority, date-range filters
 * and sort by any field in any direction.
 *
 * Props:
 * isOpen boolean
 * onClose () => void
 * filters object (current values)
 * onApply (filters, sort) => void
 * filterFields array of { key, label, type:'text'|'select'|'date', options? }
 * sortFields array of { key, label }
 */
import { useState, useEffect } from 'react'

const FilterSortPanel = ({
    isOpen,
    onClose,
    filters: initFilters = {},
    onApply,
    filterFields = [],
    sortFields = [],
}) => {
    const [localFilters, setLocalFilters] = useState(initFilters)
    const [sortBy, setSortBy] = useState(initFilters._sortBy || '')
    const [sortDir, setSortDir] = useState(initFilters._sortDir || 'asc')

    useEffect(() => {
        if (isOpen) {
            setLocalFilters(initFilters)
            setSortBy(initFilters._sortBy || '')
            setSortDir(initFilters._sortDir || 'asc')
        }
    }, [isOpen]) // eslint-disable-line react-hooks/exhaustive-deps

    const setField = (key, val) => setLocalFilters((p) => ({ ...p, [key]: val }))

    const handleApply = () => {
        const combined = { ...localFilters, _sortBy: sortBy, _sortDir: sortDir }
        if (onApply) onApply(combined, { sortBy, sortDir })
        onClose()
    }

    const handleReset = () => {
        const empty = Object.fromEntries(filterFields.map((f) => [f.key, '']))
        setLocalFilters(empty)
        setSortBy('')
        setSortDir('asc')
    }

    const inp = 'w-full px-3 py-2 rounded-md border border-hairline bg-surface-1 text-ink text-body placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-primary-focus/50 transition-colors'

    const activeCount = filterFields.filter((f) => localFilters[f.key]).length + (sortBy ? 1 : 0)

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-30 bg-semantic-overlay/50"
                    onClick={onClose}
                />
            )}

            {/* Panel */}
            <div
                className={`fixed top-0 right-0 h-full z-40 w-80 bg-canvas border-l border-hairline -2xl flex flex-col transition-transform duration-300 ${isOpen ? 'translate-x-0' : 'translate-x-full'
                    }`}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-hairline flex-shrink-0">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-ink-muted text-xl">filter_list</span>
                        <h3 className="text-card-title text-ink">Filter &amp; Sort</h3>
                        {activeCount > 0 && (
                            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary text-white text-[10px] font-bold">
                                {activeCount}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-md text-ink-subtle hover:bg-surface-1 hover:text-ink transition-colors"
                    >
                        <span className="material-symbols-outlined text-lg">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-5 space-y-6">
                    {/* ── Filters ── */}
                    {filterFields.length > 0 && (
                        <section>
                            <p className="text-eyebrow text-ink-subtle uppercase tracking-wider mb-3">
                                Filters
                            </p>
                            <div className="space-y-4">
                                {filterFields.map((field) => (
                                    <div key={field.key}>
                                        <label className="block text-caption text-ink-muted mb-1.5">
                                            {field.label}
                                        </label>
                                        {field.type === 'select' ? (
                                            <select
                                                value={localFilters[field.key] || ''}
                                                onChange={(e) => setField(field.key, e.target.value)}
                                                className={inp}
                                            >
                                                <option value="">Any</option>
                                                {(field.options || []).map((o) => (
                                                    <option key={o.value ?? o} value={o.value ?? o} className="bg-surface-1">
                                                        {o.label ?? o}
                                                    </option>
                                                ))}
                                            </select>
                                        ) : field.type === 'date' ? (
                                            <input
                                                type="date"
                                                value={localFilters[field.key] || ''}
                                                onChange={(e) => setField(field.key, e.target.value)}
                                                className={inp}
                                            />
                                        ) : (
                                            <input
                                                type="text"
                                                value={localFilters[field.key] || ''}
                                                onChange={(e) => setField(field.key, e.target.value)}
                                                placeholder={field.placeholder || ''}
                                                className={inp}
                                            />
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* ── Sort ── */}
                    {sortFields.length > 0 && (
                        <section>
                            <p className="text-eyebrow text-ink-subtle uppercase tracking-wider mb-3">
                                Sort
                            </p>
                            <div className="space-y-3">
                                <div>
                                    <label className="block text-caption text-ink-muted mb-1.5">Sort By</label>
                                    <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className={inp}>
                                        <option value="">Default</option>
                                        {sortFields.map((f) => (
                                            <option key={f.key} value={f.key} className="bg-surface-1">{f.label}</option>
                                        ))}
                                    </select>
                                </div>
                                {sortBy && (
                                    <div className="flex gap-2">
                                        {['asc', 'desc'].map((d) => (
                                            <button
                                                key={d}
                                                onClick={() => setSortDir(d)}
                                                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-pill text-button transition-colors ${sortDir === d
                                                        ? 'bg-surface-2 text-ink'
                                                        : 'bg-canvas text-ink-subtle hover:text-ink'
                                                    }`}
                                            >
                                                <span className="material-symbols-outlined text-base">
                                                    {d === 'asc' ? 'arrow_upward' : 'arrow_downward'}
                                                </span>
                                                {d === 'asc' ? 'Ascending' : 'Descending'}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </section>
                    )}
                </div>

                {/* Footer */}
                <div className="flex gap-3 px-5 py-4 border-t border-hairline flex-shrink-0">
                    <button
                        onClick={handleReset}
                        className="flex-1 bg-surface-1 text-ink text-button rounded-md border border-hairline hover:bg-surface-2 transition-colors py-2"
                    >
                        Reset
                    </button>
                    <button
                        onClick={handleApply}
                        className="flex-1 bg-primary text-on-primary text-button rounded-md hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary-focus/50 transition-colors py-2"
                    >
                        Apply Filters
                    </button>
                </div>
            </div>
        </>
    )
}

export default FilterSortPanel
