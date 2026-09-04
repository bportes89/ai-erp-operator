import "./styles.css";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata = {
  title: "AIOperator",
  description: "Pedidos B2B executados com segurança no ERP",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" data-theme="dark">
      <body className={inter.className}>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('ao_theme');document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark')}catch(e){document.documentElement.setAttribute('data-theme','dark')}`,
          }}
        />
        {children}
      </body>
    </html>
  );
}