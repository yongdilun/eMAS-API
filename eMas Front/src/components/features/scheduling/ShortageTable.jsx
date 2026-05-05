const ShortageTable = ({ shortages = [], focusedEntityId }) => {
 return (
 <div className="rounded-lg border border-hairline overflow-hidden">
 <div className="px-3 py-2 bg-surface-2 border-b border-hairline">
 <p className="text-xs font-semibold text-ink">
 Material Shortages ({shortages.length})
 </p>
 </div>
 <div className="max-h-[460px] overflow-auto">
 <table className="w-full text-xs">
 <thead className="bg-surface-2 sticky top-0">
 <tr className="text-left text-ink-subtle">
 <th className="px-3 py-2">Entity</th>
 <th className="px-3 py-2">Step</th>
 <th className="px-3 py-2">Deficit</th>
 <th className="px-3 py-2">Start</th>
 <th className="px-3 py-2">Status</th>
 </tr>
 </thead>
 <tbody>
 {shortages.map((s, idx) => {
 const entityId = s.material_id || s.material_name || `row-${idx}`
 const isFocused = focusedEntityId && String(focusedEntityId) === String(entityId)
 return (
 <tr
 key={`${entityId}-${idx}`}
 className={`border-t border-hairline ${
 isFocused ? 'bg-amber-50 dark:bg-amber-900/20' : ''
 }`}
 >
 <td className="px-3 py-2 text-ink">{entityId}</td>
 <td className="px-3 py-2 text-ink-subtle">{s.job_step_id || '—'}</td>
 <td className="px-3 py-2 text-ink-subtle">{s.max_deficit ?? 0}</td>
 <td className="px-3 py-2 text-ink-subtle">
 {s.shortage_start_at ? new Date(s.shortage_start_at).toLocaleString() : '—'}
 </td>
 <td className="px-3 py-2">
 <span className={`px-2 py-0.5 rounded text-[10px] ${
 s.all_step_materials_feasible === false
 ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'
 : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
 }`}>
 {s.all_step_materials_feasible === false ? 'Blocked' : 'Feasible'}
 </span>
 </td>
 </tr>
 )
 })}
 </tbody>
 </table>
 </div>
 </div>
 )
}

export default ShortageTable
