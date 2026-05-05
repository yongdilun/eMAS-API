const MachineTable = ({ machines, onEdit, onView }) => {
 const getStatusBadge = (status) => {
 const statusConfig = {
 Running: {
 bg: 'bg-green-500/10',
 text: 'text-green-400',
 dot: 'bg-green-400',
 },
 Idle: {
 bg: 'bg-yellow-500/10',
 text: 'text-yellow-400',
 dot: 'bg-yellow-400',
 },
 Maintenance: {
 bg: 'bg-blue-500/10',
 text: 'text-blue-400',
 dot: 'bg-blue-400',
 },
 Error: {
 bg: 'bg-red-500/10',
 text: 'text-red-400',
 dot: 'bg-red-400',
 },
 }

 const config = statusConfig[status] || statusConfig.Idle

 return (
 <span
 className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${config.bg} ${config.text}`}
 >
 <span className={`h-2 w-2 rounded-full ${config.dot}`}></span>
 {status}
 </span>
 )
 }

 return (
 <div className="flex-1 overflow-hidden rounded-lg border border-hairline bg-background-light dark:bg-[#0A192F]">
 <div className="overflow-x-auto">
 <table className="w-full min-w-[600px] text-sm text-left">
 <thead className="bg-surface-2 text-xs uppercase text-ink-subtle">
 <tr>
 <th className="px-6 py-3 font-medium" scope="col">
 Machine ID
 </th>
 <th className="px-6 py-3 font-medium" scope="col">
 Status
 </th>
 <th className="px-6 py-3 font-medium" scope="col">
 Type
 </th>
 <th className="px-6 py-3 font-medium" scope="col">
 Last Maintenance
 </th>
 <th className="px-6 py-3 font-medium text-right" scope="col">
 Actions
 </th>
 </tr>
 </thead>
 <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
 {machines.map((machine) => (
 <tr
 key={machine.id}
 className="hover:bg-surface-2 dark:hover:bg-primary/10"
 >
 <td className="px-6 py-4 whitespace-nowrap font-medium text-ink">
 {machine.id}
 </td>
 <td className="px-6 py-4">{getStatusBadge(machine.status)}</td>
 <td className="px-6 py-4 text-ink">{machine.type}</td>
 <td className="px-6 py-4 text-ink">
 {machine.lastMaintenance}
 </td>
 <td className="px-6 py-4 text-right">
 <button
 onClick={() => onEdit && onEdit(machine)}
 className="p-2 text-ink-subtle hover:text-primary rounded-lg"
 >
 <span className="material-symbols-outlined text-xl">edit</span>
 </button>
 <button
 onClick={() => onView && onView(machine)}
 className="p-2 text-ink-subtle hover:text-primary rounded-lg"
 >
 <span className="material-symbols-outlined text-xl">visibility</span>
 </button>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>
 )
}

export default MachineTable

