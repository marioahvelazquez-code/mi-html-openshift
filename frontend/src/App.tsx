import Header from "./components/Header";
import Footer from "./components/Footer";
import MenuLateral from "./components/MenuLateral";
import Separador from "./components/Separador";
import PantallaLogin from "./components/PantallaLogin";
import CargaExcel from "./modules/cargaExcel/CargaExcel";
import RevisarFicha from "./modules/RevisarFicha/RevisarFicha";
import type { VistaActiva } from "./modules/cargaExcel/types";
import { useState } from "react";
import CarruselHome from "./components/CarruselHome";

function App() {
  const [vistaActiva, setVistaActiva] = useState<VistaActiva>("menu");
  const [showMenu, setShowMenu] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const handleLogout = () => {
    setIsAuthenticated(false);
    setVistaActiva("menu");
    setShowMenu(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="app-layout">
        <Header onOpenMenu={() => {}} showMenu={false} />

        <Separador />

        <main className="app-content">
          <PantallaLogin
            onLoginSuccess={() => {
              setVistaActiva("RevisaPPTx");
              setIsAuthenticated(true);
            }}
          />
        </main>

        <Footer />
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* HEADER */}
      <Header onOpenMenu={() => setShowMenu(true)} showMenu={showMenu} />

      <Separador />

      {/* CONTENIDO */}
      <main className="app-content">
        {["menu", "inicio"].includes(vistaActiva) && (
          <>
            <CarruselHome />
          </>
        )}

        {vistaActiva === "excel" && (
          <>
            <div className="bloque-global">
              <CargaExcel />
            </div>
          </>
        )}

        {vistaActiva === "RevisaPPTx" && (
          <>
            <div className="bloque-global">
              <RevisarFicha />
            </div>
          </>
        )}
      </main>

      {/* MENÚ LATERAL 1 */}
      <MenuLateral
        show={showMenu}
        onHide={() => setShowMenu(false)}
        onOpenCargaMenu={(vista) => {
          setVistaActiva(vista);
          setShowMenu(false); //
        }}
        onLogout={handleLogout}
      />

      {/* FOOTER */}
      <Footer />
    </div>
  );
}

export default App;
