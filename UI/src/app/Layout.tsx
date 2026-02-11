import { ReactNode } from "react";


export default function AppLayout({ children }: { children: ReactNode }) {
    return (
        <div className="flex h-screen">
            <aside className="w-64 border-r p-4">Sidebar</aside>
            <main className="flex-1 p-4">{children}</main>
        </div>
    );
}