const InventoryTable = ({ items, onActionClick }) => {
    const getStatusBadge = (status) => {
        const statusConfig = {
            'In Stock': {
                bg: 'bg-green-500/20',
                text: 'text-green-400',
                dot: 'bg-green-400',
            },
            'Low Stock': {
                bg: 'bg-yellow-500/20',
                text: 'text-yellow-400',
                dot: 'bg-yellow-400',
            },
            'Out of Stock': {
                bg: 'bg-red-500/20',
                text: 'text-red-400',
                dot: 'bg-red-400',
            },
        }

        const config = statusConfig[status] || statusConfig['In Stock']

        return (
            <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}
            >
                <span className={`w-2 h-2 ${config.dot} rounded-full`}></span>
                {status}
            </span>
        )
    }

    return (
        <div className="bg-surface-1 rounded-xl overflow-hidden border border-hairline">
            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="bg-surface-2">
                        <tr className="border-b border-hairline">
                            <th className="px-6 py-4 font-semibold text-sm text-ink-muted">Material ID</th>
                            <th className="px-6 py-4 font-semibold text-sm text-ink-muted">Material Name</th>
                            <th className="px-6 py-4 font-semibold text-sm text-ink-muted">Current Stock</th>
                            <th className="px-6 py-4 font-semibold text-sm text-ink-muted">Min Required</th>
                            <th className="px-6 py-4 font-semibold text-sm text-ink-muted">Status</th>
                            <th className="px-6 py-4 font-semibold text-sm text-ink-muted"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item) => (
                            <tr
                                key={item.id}
                                className="border-b border-hairline hover:bg-surface-2 transition-colors last:border-b-0"
                            >
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-ink-subtle">{item.id}</td>
                                <td className="px-6 py-4 whitespace-nowrap font-medium text-ink">
                                    {item.name}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-ink">{item.currentStock}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-ink">{item.minStock}</td>
                                <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(item.status)}</td>
                                <td className="px-6 py-4 text-right">
                                    <button
                                        onClick={() => onActionClick && onActionClick(item)}
                                        className="p-1.5 text-ink-subtle hover:text-ink dark:hover:text-white rounded-md hover:bg-surface-2 transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-lg">more_horiz</span>
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

export default InventoryTable

