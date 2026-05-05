const ThemeToggle = ({ isDark, onToggle }) => {
 return (
  <div className="flex items-center gap-4">
    <span className="text-sm text-ink-subtle">Light</span>
    <label className="relative inline-flex items-center cursor-pointer group">
      <input
        type="checkbox"
        checked={isDark}
        onChange={onToggle}
        className="sr-only peer"
      />
      <div className="w-11 h-6 bg-hairline-strong border border-hairline rounded-full transition-colors
        peer-checked:bg-primary peer-checked:border-primary-hover
        after:content-[''] after:absolute after:top-[3px] after:left-[3px] 
        after:bg-white after:rounded-full after:h-[18px] after:w-[18px] after:transition-all 
        after:shadow-sm peer-checked:after:translate-x-[20px]" />
    </label>
    <span className="text-sm text-ink">Dark</span>
  </div>
 )
}

export default ThemeToggle

