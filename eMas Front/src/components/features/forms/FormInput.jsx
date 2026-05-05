const FormInput = ({ label, type = 'text', value, onChange, error, ...props }) => {
 return (
 <div className="mb-md">
 <label className="block text-body-sm font-medium text-ink mb-xs">
 {label}
 </label>
 <input
 type={type}
 value={value}
 onChange={onChange}
 className={`w-full px-3 py-2 rounded-md border bg-surface-1 text-ink text-body placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-primary-focus/50 transition-colors ${
 error ? 'border-red-500' : 'border-hairline'
 }`}
 {...props}
 />
 {error && <p className="mt-1 text-caption text-red-500">{error}</p>}
 </div>
 )
}

export default FormInput


