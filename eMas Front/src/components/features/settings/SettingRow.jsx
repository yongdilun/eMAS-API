const SettingRow = ({ title, description, children }) => {
 return (
 <div className="flex items-center justify-between">
 <div>
 <h3 className="text-base font-medium text-ink">{title}</h3>
 <p className="text-sm text-ink-subtle dark:text-[#9ab4bc]">{description}</p>
 </div>
 <div>{children}</div>
 </div>
 )
}

export default SettingRow

