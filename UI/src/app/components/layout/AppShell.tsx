"use client";

import React from "react";

/*
  This file is INTENTIONALLY non-functional.
  It defines layout + components ONLY.
  No auth wiring, no API calls, no RBAC logic yet.
*/

// ─────────────────────────────────────────────
// Layout Shell
// ─────────────────────────────────────────────

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen w-screen flex overflow-hidden">
      <Sidebar />
      <main className="flex-1 bg-gray-50 overflow-auto">
        <TopBar />
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────

function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r flex flex-col">
      <div className="p-4 font-semibold text-lg">DMS</div>

      <nav className="flex-1 px-2 space-y-1">
        <NavItem label="Documents" />
        <NavItem label="Upload" />
        <NavItem label="Admin" />
      </nav>

      <div className="p-4 text-sm text-gray-500">© Internal</div>
    </aside>
  );
}

function NavItem({ label }: { label: string }) {
  return (
    <div className="px-3 py-2 rounded-lg hover:bg-gray-100 cursor-pointer">
      {label}
    </div>
  );
}

function TopBar() {
  return (
    <header className="h-14 bg-white border-b flex items-center justify-between px-6">
      <div className="font-medium">Document Management System</div>
      <UserMenu />
    </header>
  );
}

function UserMenu() {
  return (
    <div className="text-sm text-gray-600">user@example.com</div>
  );
}

// ─────────────────────────────────────────────
// Pages (Skeletons)
// ─────────────────────────────────────────────

export function DocumentsPage() {
  return (
    <section>
      <h1 className="text-xl font-semibold mb-4">Documents</h1>
      <DocumentTable />
    </section>
  );
}

export function UploadPage() {
  return (
    <section>
      <h1 className="text-xl font-semibold mb-4">Upload Document</h1>
      <UploadDropzone />
    </section>
  );
}

export function AdminPage() {
  return (
    <section>
      <h1 className="text-xl font-semibold mb-4">Administration</h1>
      <AdminPanel />
    </section>
  );
}

// ─────────────────────────────────────────────
// Components (Skeletons)
// ─────────────────────────────────────────────

function DocumentTable() {
  return (
    <div className="border rounded-lg bg-white">
      <div className="p-4 text-gray-500">Document table goes here</div>
    </div>
  );
}

function UploadDropzone() {
  return (
    <div className="border-2 border-dashed rounded-lg p-8 text-center text-gray-500">
      Drag & drop files here
    </div>
  );
}

function AdminPanel() {
  return (
    <div className="grid grid-cols-3 gap-4">
      <AdminCard title="Users" />
      <AdminCard title="Roles" />
      <AdminCard title="Permissions" />
    </div>
  );
}

function AdminCard({ title }: { title: string }) {
  return (
    <div className="border rounded-lg bg-white p-4">
      <div className="font-medium">{title}</div>
    </div>
  );
}
