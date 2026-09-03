import "./styles.css";

export const metadata = {
  title: "AI ERP Operator",
  description: "Pedidos B2B executados com segurança no ERP",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('ao_theme');if(t==='dark')document.documentElement.setAttribute('data-theme','dark')}catch(e){}`,
          }}
        />
        {children}
      </body>
    </html>
  );
}