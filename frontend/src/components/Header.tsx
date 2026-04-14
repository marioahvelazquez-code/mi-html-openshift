import logoBlanco from "../assets/img/logo-gob-mx.png";
import dpti from "../assets/img/dpti.png";

export default function Header() {
  const descargarProtegido = async (endpoint: string, nombre: string) => {
    const password = window.prompt("Ingresa la contraseña para descargar");
    if (!password) return;

    try {
      const response = await fetch(endpoint, {
        method: "GET",
        headers: {
          "X-Download-Password": password,
        },
      });

      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { message?: string };
        alert(data.message ?? "No fue posible descargar el archivo.");
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = nombre;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch {
      alert("Error de conexión al descargar.");
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
              void descargarProtegido("/api/catalogos/descargar_bitacora/", "bitacora_fotos.txt");
            }}
            style={{ color: "#ffffff", fontSize: "0.95rem", textDecoration: "none" }}
          >
            Descargar bitácora
          </a>
          <a
            href="#"
            onClick={(event) => {
              event.preventDefault();
              void descargarProtegido("/api/catalogos/descargar_todo/", "fotos.zip");
            }}
            style={{ color: "#ffffff", fontSize: "0.95rem", textDecoration: "none" }}
          >
            Descargar imágenes
          </a>
        </div>
      </div>
    </header>
  );
}
