const Table = ({ headers, data }) => {
 return (
 <div className="overflow-x-auto">
 <table className="min-w-full divide-y divide-hairline">
 <thead className="bg-canvas">
 <tr>
 {headers.map((header, index) => (
 <th
 key={index}
 className="px-6 py-4 text-left text-caption text-ink-muted uppercase tracking-wider"
 >
 {header}
 </th>
 ))}
 </tr>
 </thead>
 <tbody className="bg-canvas divide-y divide-hairline">
 {data.map((row, rowIndex) => (
 <tr key={rowIndex} className="hover:bg-surface-1 transition-colors">
 {row.map((cell, cellIndex) => (
 <td key={cellIndex} className="px-6 py-4 whitespace-nowrap text-body text-ink">
 {cell}
 </td>
 ))}
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )
}

export default Table

