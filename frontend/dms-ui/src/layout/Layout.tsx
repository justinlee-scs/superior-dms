import { type ReactNode } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1 }}>
        <Header onUpload={function (): void {
                  throw new Error("Function not implemented.");
              } } loading={false} />
        <main style={{ padding: "1rem" }}>{children}</main>
      </div>
    </div>
  );
}
