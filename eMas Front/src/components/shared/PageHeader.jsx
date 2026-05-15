const PageHeader = ({ title, subtitle, children, className = ''
}) => {
    return (
        <header className={`mb-6 ${className}`}>
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-[4px]">
                    <h1 className="text-headline text-ink font-display">
                        {title}
                    </h1>
                    {subtitle && (
                        <p className="text-body-sm text-ink-muted">
                            {subtitle}
                        </p>
                    )}
                </div>
                {children && (
                    <div className="flex items-center gap-3">
                        {children}
                    </div>
                )}
            </div>
        </header>
    )
}

export default PageHeader

