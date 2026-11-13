import "../styles/globals.css";

export const metadata = {
  title: "AgriChain AI — Cold Chain Dashboard",
  description: "Predictive cold-chain agritech quality & spoilage tracking",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="light">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
      </head>
      <body className="font-sans antialiased text-on-background bg-background min-h-screen">
        {children}
      </body>
    </html>
  );
}
