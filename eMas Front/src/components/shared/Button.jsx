const Button = ({ children, variant = 'primary', className = '', ...props }) => {
    const baseClasses = 'px-[14px] py-[8px] rounded-md text-button transition-all duration-200 active:scale-95 flex items-center justify-center'
    const variants = {
        primary: 'bg-primary text-on-primary hover:bg-primary-hover',
        secondary: 'bg-surface-2 text-ink border border-hairline hover:bg-surface-3',
        tertiary: 'bg-transparent text-ink hover:bg-surface-2',
        inverse: 'bg-inverse-surface-1 text-inverse-ink hover:bg-inverse-surface-2',
    }

    return (
        <button className={`${baseClasses} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    )
}

export default Button


