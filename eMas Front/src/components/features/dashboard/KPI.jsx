const KPI = ({ title, value, change, isPositive = true, loading = false }) => {
 const changeColor = isPositive ? 'text-green-400' : 'text-red-400'
 const changeIcon = isPositive ? 'arrow_upward' : 'arrow_downward'
 const changeSign = isPositive ? '+' : '-'

 return (
 <div className="flex flex-col gap-2 rounded-xl p-6 border border-hairline bg-surface-1">
 <p className="text-ink-subtle text-base font-medium leading-normal">{title}</p>
 {loading ? (
 <div className="h-9 w-24 bg-gray-200 dark:bg-white/10 rounded animate-pulse" />
 ) : (
 <p className="text-ink tracking-tight text-3xl font-bold leading-tight">{value}</p>
 )}
 {change != null && !loading && (
 <p className={`${changeColor} text-sm font-medium leading-normal flex items-center gap-1`}>
 <span className="material-symbols-outlined text-base">{changeIcon}</span>
 {changeSign}{Math.abs(change)}%
 </p>
 )}
 </div>
 )
}

export default KPI
