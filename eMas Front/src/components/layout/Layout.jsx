import Sidebar from './Sidebar'

const Layout = ({ children }) => {
 return (
 <div className="relative flex h-screen w-full overflow-hidden bg-canvas text-ink">
 <Sidebar />
 <main className="flex-1 flex flex-col bg-canvas overflow-hidden">
 <div className="flex-1 overflow-auto">
 <div className="max-w-7xl mx-auto w-full">
 {children}
 </div>
 </div>
 </main>
 </div>
 )
}

export default Layout


