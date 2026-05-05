const EmptyState = ({ message, icon, action }) => {
 return (
 <div className="flex flex-col items-center justify-center p-xl text-center">
 {icon && <div className="text-6xl mb-md text-ink-subtle">{icon}</div>}
 <p className="text-ink-muted text-body-lg mb-md">{message}</p>
 {action && action}
 </div>
 )
}

export default EmptyState


