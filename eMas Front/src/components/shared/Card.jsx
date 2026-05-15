const Card = ({ children, className = '' }) => {
    return (
        <div className={`bg-surface-1 rounded-xl border border-hairline p-lg ${className}`}>
            {children}
        </div>
    )
}

export default Card


