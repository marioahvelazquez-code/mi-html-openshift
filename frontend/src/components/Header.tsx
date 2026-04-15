import { useState } from "react";
import logoBlanco from "../assets/img/logo-gob-mx.png";
import dpti from "../assets/img/dpti.png";

export default function Header() {
  const [modalDescargaAbierto, setModalDescargaAbierto] = useState(false);
  const [passwordDescarga, setPasswordDescarga] = useState("");
  const [errorDescarga, setErrorDescarga] = useState("");
  const [descargando, setDescargando] = useState(false);

  const [objetivoDescarga, setObjetivoDescarga] = useState<{ endpoint: string; nombre: string } | null>(null);

  const abrirModalDescarga = (endpoint: string, nombre: string) => {
    setObjetivoDescarga({ endpoint, nombre });
    setPasswordDescarga("");
    setErrorDescarga("");
    setModalDescargaAbierto(true);
  };

  const cerrarModalDescarga = () => {
    if (descargando) return;
    setModalDescargaAbierto(false);
    setPasswordDescarga("");
    setErrorDescarga("");
    setObjetivoDescarga(null);
  };

  const confirmarDescarga = async () => {
    if (!objetivoDescarga) return;
    if (!passwordDescarga.trim()) {
      setErrorDescarga("Ingresa la contraseña para descargar.");
      return;
    }

    setDescargando(true);
    setErrorDescarga("");

    try {
      const response = await fetch(objetivoDescarga.endpoint, {
        method: "GET",
        headers: {
          "X-Download-Password": passwordDescarga.trim(),
        },
      });

      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { message?: string };
        setErrorDescarga(data.message ?? "No fue posible descargar el archivo.");
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = objetivoDescarga.nombre;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      cerrarModalDescarga();
    } catch {
      setErrorDescarga("Error de conexión al descargar.");
    } finally {
      setDescargando(false);
    }
  };

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
            href="#"
            onClick={(event) => {
              event.preventDefault();
              abrirModalDescarga("/api/catalogos/descargar_bitacora/", "bitacora_operaciones.csv");
            }}
            style={{ color: "#ffffff", fontSize: "0.95rem", textDecoration: "none" }}
          >
            Descargar bitácora
          </a>
        </div>
      </div>

      {modalDescargaAbierto && (
        <div className="descarga-modal-overlay" onClick={cerrarModalDescarga}>
          <div className="descarga-modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="descarga-modal-badge">Seguridad</div>
            <h3 className="descarga-modal-title">Ingresa contraseña</h3>
            <p className="descarga-modal-message">
              Para descargar la bitácora, captura la contraseña de acceso.
            </p>

            <input
              type="password"
              className="descarga-modal-input"
              value={passwordDescarga}
              onChange={(event) => setPasswordDescarga(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void confirmarDescarga();
                }
              }}
              placeholder="Contraseña"
              autoFocus
              disabled={descargando}
            />

            {errorDescarga && <p className="descarga-modal-error">{errorDescarga}</p>}

            <div className="descarga-modal-actions">
              <button type="button" className="descarga-modal-btn descarga-modal-btn-secondary" onClick={cerrarModalDescarga} disabled={descargando}>
                Cancelar
              </button>
              <button type="button" className="descarga-modal-btn" onClick={() => void confirmarDescarga()} disabled={descargando}>
                {descargando ? "Descargando..." : "Descargar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
