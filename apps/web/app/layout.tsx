import "./globals.css";
import { ToastProvider } from "@/components/ui/toast";

export const metadata = {
  title: "Co-op Game Recs",
  description: "Group recommendations for cooperative games"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}

