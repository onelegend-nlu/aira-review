import type {
  Metadata,
} from "next";

import "./globals.css";


export const metadata:
Metadata = {
  title:
    "AIRA | AI Retrieval Assistant",

  description:
    "Trợ lý học tập thông minh dựa trên RAG",
};


export default function RootLayout({
  children,
}: Readonly<{
  children:
    React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>
        {children}
      </body>
    </html>
  );
}