import { useState } from "react";
import "./fotos.css";

const DELEGACIONES = [
  "Aguascalientes",
  "Baja California",
  "Baja California Sur",
  "Campeche",
  "Chiapas",
  "Chihuahua",
  "Ciudad de Mexico Norte",
  "Ciudad de Mexico Sur",
  "Coahuila",
  "Colima",
  "Durango",
  "Guanajuato",
  "Guerrero",
  "Hidalgo",
  "Jalisco",
  "Mexico Oriente",
  "Mexico Poniente",
  "Michoacan",
  "Morelos",
  "Nayarit",
  "Nuevo Leon",
  "Oaxaca",
  "Puebla",
  "Queretaro",
  "Quintana Roo",
  "San Luis Potosi",
  "Sinaloa",
  "Sonora",
  "Tabasco",
  "Tamaulipas",
  "Tlaxcala",
  "Veracruz Norte",
  "Veracruz Sur",
  "Yucatan",
  "Zacatecas",
];

const TIPOS_CARGO = ["Titular de la unidad", "Enlace operativo", "Enlace ejecutivo"];

export default function FotosPage() {
  const [delegacion, setDelegacion] = useState("");
  const [titularUnidad, setTitularUnidad] = useState("");
  const [nombreUsuario, setNombreUsuario] = useState("");
  const [cargoUsuario, setCargoUsuario] = useState("");
  const [correoInstitucional, setCorreoInstitucional] = useState("");
  const [correoPersonal, setCorreoPersonal] = useState("");
  const [telefono, setTelefono] = useState("");
  const [area, setArea] = useState("");
  const [tipoCargo, setTipoCargo] = useState("");
  const [error, setError] = useState("");
  const [guardadoExitoso, setGuardadoExitoso] = useState(false);
  const [modalGuardadoAbierto, setModalGuardadoAbierto] = useState(false);

  const limpiarFormulario = () => {
    setDelegacion("");
    setTitularUnidad("");
    setNombreUsuario("");
    setCargoUsuario("");
    setCorreoInstitucional("");
    setCorreoPersonal("");
    setTelefono("");
    setArea("");
    setTipoCargo("");
  };

  const manejarGuardar = async () => {
    const faltantes = [
      ["Delegacion", delegacion],
      ["Nombre del titular de la unidad", titularUnidad],
      ["Nombre", nombreUsuario],
      ["Cargo", cargoUsuario],
      ["Correo institucional", correoInstitucional],
      ["Correo personal", correoPersonal],
      ["Telefono", telefono],
      ["Area", area],
      ["Tipo de cargo", tipoCargo],
    ].filter(([, valor]) => !String(valor).trim());

    if (faltantes.length > 0) {
      setError(`Completa los campos requeridos: ${faltantes.map(([campo]) => campo).join(", ")}.`);
      return;
    }

    setError("");
    setGuardadoExitoso(false);
    try {
      const respuesta = await fetch("/api/catalogos/guardar_inicio_operaciones/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          delegacion,
          titular_unidad: titularUnidad,
          nombre_usuario: nombreUsuario,
          cargo_usuario: cargoUsuario,
          correo_institucional: correoInstitucional,
          correo_personal: correoPersonal,
          telefono,
          area,
          tipo_cargo: tipoCargo,
        }),
      });

      const data = (await respuesta.json()) as { ok?: boolean; message?: string };
      if (!respuesta.ok || !data.ok) {
        setGuardadoExitoso(false);
        setError(data.message ?? "No fue posible guardar el registro.");
        return;
      }

      setGuardadoExitoso(true);
      setError("");
      setModalGuardadoAbierto(true);
      limpiarFormulario();
    } catch {
      setGuardadoExitoso(false);
      setError("No fue posible conectar con el servidor.");
    }
  };

  const cerrarModalGuardado = () => {
    setModalGuardadoAbierto(false);
  };

  return (
    <div className="fotos-page">
      <div className="fotos-shell">
        <h3 className="fotos-title">Datos de acceso</h3>

        <div className="fotos-form">
          <section className="fotos-section">
            <h4 className="fotos-section-title">Datos de la institucion</h4>
            <div className="fotos-grid fotos-grid-2">
              <div className="fotos-field">
                <label htmlFor="delegacion" className="fotos-label">Delegacion</label>
                <div className="fotos-select-wrapper">
                  <select
                    id="delegacion"
                    className="fotos-select"
                    value={delegacion}
                    onChange={(event) => setDelegacion(event.target.value)}
                    required
                  >
                    <option value="">Selecciona una delegacion</option>
                    {DELEGACIONES.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="fotos-field">
                <label htmlFor="titular-unidad" className="fotos-label">Nombre del titular de la unidad</label>
                <input
                  id="titular-unidad"
                  type="text"
                  className="fotos-select"
                  value={titularUnidad}
                  onChange={(event) => setTitularUnidad(event.target.value)}
                  placeholder="Escribe el nombre del titular"
                  required
                />
              </div>
            </div>
          </section>

          <section className="fotos-section">
            <h4 className="fotos-section-title">Datos del usuario</h4>
            <div className="fotos-grid fotos-grid-3">
              <div className="fotos-field">
                <label htmlFor="nombre-usuario" className="fotos-label">Nombre</label>
                <input
                  id="nombre-usuario"
                  type="text"
                  className="fotos-select"
                  value={nombreUsuario}
                  onChange={(event) => setNombreUsuario(event.target.value)}
                  placeholder="Nombre del usuario"
                  required
                />
              </div>

              <div className="fotos-field">
                <label htmlFor="cargo-usuario" className="fotos-label">Cargo</label>
                <input
                  id="cargo-usuario"
                  type="text"
                  className="fotos-select"
                  value={cargoUsuario}
                  onChange={(event) => setCargoUsuario(event.target.value)}
                  placeholder="Cargo del usuario"
                  required
                />
              </div>

              <div className="fotos-field">
                <label htmlFor="correo-institucional" className="fotos-label">Correo institucional</label>
                <input
                  id="correo-institucional"
                  type="email"
                  className="fotos-select"
                  value={correoInstitucional}
                  onChange={(event) => setCorreoInstitucional(event.target.value)}
                  placeholder="usuario@imss.gob.mx"
                  required
                />
              </div>

              <div className="fotos-field">
                <label htmlFor="correo-personal" className="fotos-label">Correo personal</label>
                <input
                  id="correo-personal"
                  type="email"
                  className="fotos-select"
                  value={correoPersonal}
                  onChange={(event) => setCorreoPersonal(event.target.value)}
                  placeholder="usuario@correo.com"
                  required
                />
              </div>

              <div className="fotos-field">
                <label htmlFor="telefono" className="fotos-label">Telefono</label>
                <input
                  id="telefono"
                  type="tel"
                  className="fotos-select"
                  value={telefono}
                  onChange={(event) => setTelefono(event.target.value)}
                  placeholder="10 digitos"
                  required
                />
              </div>

              <div className="fotos-field">
                <label htmlFor="area" className="fotos-label">Area</label>
                <input
                  id="area"
                  type="text"
                  className="fotos-select"
                  value={area}
                  onChange={(event) => setArea(event.target.value)}
                  placeholder="Area de adscripcion"
                  required
                />
              </div>

              <div className="fotos-field fotos-field-full">
                <label htmlFor="tipo-cargo" className="fotos-label">Tipo de cargo</label>
                <div className="fotos-select-wrapper">
                  <select
                    id="tipo-cargo"
                    className="fotos-select"
                    value={tipoCargo}
                    onChange={(event) => setTipoCargo(event.target.value)}
                    required
                  >
                    <option value="">Selecciona una opcion</option>
                    {TIPOS_CARGO.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </section>

          {error && <p className="fotos-error">{error}</p>}

          <div className="fotos-actions">
            <button
              type="button"
              className={`fotos-btn ${guardadoExitoso ? "fotos-btn-ok" : ""}`}
              onClick={manejarGuardar}
            >
              {guardadoExitoso ? "Guardado" : "Guardar"}
            </button>
          </div>
        </div>
      </div>

      {modalGuardadoAbierto && (
        <div className="revision-modal-overlay" onClick={cerrarModalGuardado}>
          <div className="revision-modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="revision-modal-badge revision-modal-success">Completado</div>
            <h3 className="revision-modal-title">Registro realizado</h3>
            <p className="revision-modal-message">
              Los datos iniciales se guardaron correctamente.
            </p>

            <div className="fotos-modal-actions">
              <button type="button" className="fotos-btn" onClick={cerrarModalGuardado}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
