const Loading = ({ message = 'Loading...' }) => {
 return (
 <div className="flex items-center justify-center p-xl">
 <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
 <p className="ml-md text-ink-muted text-body">{message}</p>
 </div>
 )
}

export default Loading


