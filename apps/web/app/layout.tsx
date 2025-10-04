import "../styles/globals.css";
import { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <title>Home Energy Snapshot</title>
      </head>
      <body className="bg-gray-50 text-slate-800">
        {children}
      </body>
    </html>
  );
}
