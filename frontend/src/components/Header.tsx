import logoBlanco from "../assets/img/logo-gob-mx.png";
import dpti from "../assets/img/dpti.png";

export default function Header() {
  return (
    <header id="menu_principal" className="bg-verdeIMSS py-2">
      <div className="container d-flex align-items-center justify-content-between">
        <div className="d-flex align-items-center gap-3">
          <img
            src={logoBlanco}
            className="img-fluid"
            style={{ maxHeight: "50px" }}
            alt="Gobierno de Mexico"
          />

          <div style={{ width: "1px", height: "35px", background: "white" }} />

          <img
            src={dpti}
            className="img-fluid"
            style={{ maxHeight: "45px" }}
            alt="DPTI"
          />
        </div>

        <div className="d-flex align-items-center gap-3">
          <a
            href="/api/catalogos/descargar_bitacora/"
            download="bitacora_fotos.txt"
            style={{ color: "#ffffff", fontSize: "0.95rem", textDecoration: "none" }}
          >
            Descargar bitácora
          </a>
          <a
            href="/api/catalogos/descargar_todo/"
            download
            style={{ color: "#ffffff", fontSize: "0.95rem", textDecoration: "none" }}
          >
            Descargar imágenes
          </a>
        </div>
      </div>
    </header>
  );
}
