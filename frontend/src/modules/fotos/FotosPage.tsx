import { useMemo, useRef, useState } from "react";
import "./fotos.css";
import { CATALOGO_UNIDADES } from "./catalogoUnidades";

export default function FotosPage() {
  const [region, setRegion] = useState("");
  const [entidad, setEntidad] = useState("");
  const [unidad, setUnidad] = useState("");
  const [fechaInicioOperaciones, setFechaInicioOperaciones] = useState("");
  const [error, setError] = useState("");
  const [guardadoExitoso, setGuardadoExitoso] = useState(false);
  const [modalGuardadoAbierto, setModalGuardadoAbierto] = useState(false);
  const fechaInputRef = useRef<HTMLInputElement | null>(null);

  const regiones = useMemo(
    () => Array.from(new Set(CATALOGO_UNIDADES.map((item) => item.region))).sort((a, b) => a.localeCompare(b)),
    [],
  );

  const entidades = useMemo(
    () =>
      Array.from(
        new Set(
          CATALOGO_UNIDADES
            .filter((item) => !region || item.region === region)
            .map((item) => item.entidad),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [region],
  );

  const unidades = useMemo(
    () =>
      Array.from(
        new Set(
          CATALOGO_UNIDADES
            .filter((item) => (!region || item.region === region) && (!entidad || item.entidad === entidad))
            .map((item) => item.unidad),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [region, entidad],
  );

  const registroSeleccionado = useMemo(
    () => CATALOGO_UNIDADES.find((item) => item.region === region && item.entidad === entidad && item.unidad === unidad),
    [region, entidad, unidad],
  );

  const abrirCalendario = () => {
    if (!unidad || !fechaInputRef.current) return;
    const input = fechaInputRef.current as HTMLInputElement & { showPicker?: () => void };
    input.focus();
    try {
      input.showPicker?.();
    } catch {
      // Algunos navegadores lanzan excepción si showPicker no está disponible por contexto.
    }
  };

  const manejarGuardar = async () => {
    if (!region || !entidad || !unidad) {
      setError("Selecciona Region, Entidad y Unidad antes de guardar.");
      return;
    }

    if (!registroSeleccionado?.clave) {
      setError("No se encontro clave presupuestal para la unidad seleccionada.");
      return;
    }

    if (!fechaInicioOperaciones) {
      setError("Selecciona la fecha de inicio de operaciones.");
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
          clave_presupuestal: registroSeleccionado.clave,
          fecha_inicio_operaciones: fechaInicioOperaciones,
          region,
          entidad,
          unidad,
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
        <h3 className="fotos-title">Fecha de inicio de operaciones</h3>

        <div className="fotos-form">
          <div className="fotos-field">
            <label htmlFor="region" className="fotos-label">Region</label>
            <div className="fotos-select-wrapper">
              <select
                id="region"
                className="fotos-select"
                value={region}
                onChange={(event) => {
                  setRegion(event.target.value);
                  setEntidad("");
                  setUnidad("");
                  setFechaInicioOperaciones("");
                  setGuardadoExitoso(false);
                }}
              >
                <option value="">Selecciona una Region</option>
                {regiones.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="fotos-field">
            <label htmlFor="entidad" className="fotos-label">Entidad</label>
            <div className="fotos-select-wrapper">
              <select
                id="entidad"
                className="fotos-select"
                value={entidad}
                onChange={(event) => {
                  setEntidad(event.target.value);
                  setUnidad("");
                  setFechaInicioOperaciones("");
                  setGuardadoExitoso(false);
                }}
                disabled={!region}
              >
                <option value="">Selecciona una Entidad</option>
                {entidades.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="fotos-field">
            <label htmlFor="unidad" className="fotos-label">Unidad Hospitalaria</label>
            <div className="fotos-select-wrapper">
              <select
                id="unidad"
                className="fotos-select"
                value={unidad}
                onChange={(event) => {
                  setUnidad(event.target.value);
                  setGuardadoExitoso(false);
                }}
                disabled={!entidad}
              >
                <option value="">Selecciona una Unidad</option>
                {unidades.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="fotos-field">
            <label htmlFor="fecha-inicio" className="fotos-label">Fecha de inicio de operaciones</label>
            <input
              ref={fechaInputRef}
              id="fecha-inicio"
              type="date"
              className="fotos-select fotos-date-input"
              value={fechaInicioOperaciones}
              onChange={(event) => {
                setFechaInicioOperaciones(event.target.value);
                setGuardadoExitoso(false);
              }}
              onClick={abrirCalendario}
              onFocus={abrirCalendario}
              disabled={!unidad}
            />
            {!unidad && <p className="fotos-help">Selecciona una unidad para habilitar el calendario.</p>}
          </div>

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
              La fecha de inicio de operaciones se guardo correctamente.
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
