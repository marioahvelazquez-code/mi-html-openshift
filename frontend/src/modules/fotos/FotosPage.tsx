import { useEffect, useMemo, useRef, useState } from "react";
import "./fotos.css";
import { CATALOGO_UNIDADES } from "./catalogoUnidades";

const TIPOS_FOTO = [
  { id: "fachada", label: "Cargar fachada" },
  { id: "foto1", label: "Cargar foto 1" },
  { id: "foto2", label: "Cargar foto 2" },
  { id: "foto3", label: "Cargar foto 3" },
  { id: "foto4", label: "Cargar foto 4" },
] as const;

type TipoFoto = (typeof TIPOS_FOTO)[number]["id"];

const estadoInicialFotos: Record<TipoFoto, boolean> = {
  fachada: false,
  foto1: false,
  foto2: false,
  foto3: false,
  foto4: false,
};

export default function FotosPage() {
  const [region, setRegion] = useState("");
  const [entidad, setEntidad] = useState("");
  const [unidad, setUnidad] = useState("");
  const [error, setError] = useState("");
  const [fotosSubidas, setFotosSubidas] = useState<Record<TipoFoto, boolean>>(estadoInicialFotos);
  const [mostrarRegistro, setMostrarRegistro] = useState(false);
  const [listaFotos, setListaFotos] = useState<{ nombre: string; bytes: number; fecha: string }[]>([]);

  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

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

  const resetEstadoFotos = () => {
    setFotosSubidas(estadoInicialFotos);
  };

  const cargarListaFotos = async () => {
    try {
      const resp = await fetch("/api/catalogos/listar_fotos/");
      const data = (await resp.json()) as {
        ok?: boolean;
        fotos?: { nombre: string; bytes: number; fecha: string }[];
      };
      if (data.ok && data.fotos) setListaFotos(data.fotos);
    } catch {
      // ignorar error de red
    }
  };

  useEffect(() => {
    const cargarEstadoFotos = async () => {
      if (!region || !entidad || !unidad || !registroSeleccionado?.clave) {
        setFotosSubidas(estadoInicialFotos);
        return;
      }

      try {
        const params = new URLSearchParams({
          clave_presupuestal: registroSeleccionado.clave,
          region,
          entidad,
          unidad,
        });

        const response = await fetch(`/api/catalogos/fotos_cargadas/?${params.toString()}`);
        const data = (await response.json()) as {
          ok?: boolean;
          fotos?: Partial<Record<TipoFoto, boolean>>;
        };

        if (!response.ok || !data.ok || !data.fotos) {
          setFotosSubidas(estadoInicialFotos);
          return;
        }

        setFotosSubidas({
          fachada: Boolean(data.fotos.fachada),
          foto1: Boolean(data.fotos.foto1),
          foto2: Boolean(data.fotos.foto2),
          foto3: Boolean(data.fotos.foto3),
          foto4: Boolean(data.fotos.foto4),
        });
      } catch {
        setFotosSubidas(estadoInicialFotos);
      }
    };

    void cargarEstadoFotos();
  }, [region, entidad, unidad, registroSeleccionado?.clave]);

  const manejarClickFoto = (tipo: TipoFoto) => {
    if (!region || !entidad || !unidad) {
      setError("Selecciona Region, Entidad y Unidad antes de cargar una foto.");
      return;
    }

    if (!registroSeleccionado?.clave) {
      setError("No se encontro clave presupuestal para la unidad seleccionada.");
      return;
    }

    setError("");
    inputRefs.current[tipo]?.click();
  };

  const manejarArchivoSeleccionado = async (tipo: TipoFoto, archivo: File | undefined) => {
    if (!archivo) return;

    if (!registroSeleccionado?.clave) {
      setError("No se encontro clave presupuestal para la unidad seleccionada.");
      return;
    }

    const formData = new FormData();
    formData.append("clave_presupuestal", registroSeleccionado.clave);
    formData.append("region", region);
    formData.append("entidad", entidad);
    formData.append("unidad", unidad);
    formData.append("tipo", tipo);
    formData.append("foto", archivo);

    try {
      const respuesta = await fetch("/api/catalogos/subir_foto/", {
        method: "POST",
        body: formData,
      });

      const data = (await respuesta.json()) as { ok?: boolean; message?: string };
      if (!respuesta.ok || !data.ok) {
        setError(data.message ?? "Error al subir la imagen.");
        return;
      }

      setFotosSubidas((prev) => ({ ...prev, [tipo]: true }));
      setError("");
    } catch {
      setError("No fue posible conectar con el servidor.");
    }
  };

  return (
    <div className="fotos-page">
      <div className="fotos-shell">
        <h3 className="fotos-title">Carga de fotos</h3>

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
                  resetEstadoFotos();
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
                  resetEstadoFotos();
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
                  resetEstadoFotos();
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

          {error && <p className="fotos-error">{error}</p>}

          <div className="fotos-botones">
            {TIPOS_FOTO.map(({ id, label }) => (
              <div key={id} className="fotos-item">
                <input
                  ref={(el) => { inputRefs.current[id] = el; }}
                  type="file"
                  accept="image/*"
                  className="fotos-input-hidden"
                  onChange={(e) => manejarArchivoSeleccionado(id, e.target.files?.[0])}
                />
                <button
                  type="button"
                  className={`fotos-btn ${fotosSubidas[id] ? "fotos-btn-ok" : ""}`}
                  onClick={() => manejarClickFoto(id)}
                >
                  {fotosSubidas[id] ? `${label} (Cargada)` : label}
                </button>
              </div>
            ))}
          </div>

          <div className="fotos-registro">
            <button
              type="button"
              className="fotos-btn fotos-btn-registro"
              onClick={() => {
                if (!mostrarRegistro) void cargarListaFotos();
                setMostrarRegistro((prev) => !prev);
              }}
            >
              {mostrarRegistro ? "Ocultar registro" : "Ver fotos registradas"}
            </button>

            {mostrarRegistro && (
              <div className="fotos-lista">
                <div className="fotos-lista-header">
                  <span>{listaFotos.length} foto(s) registrada(s)</span>
                  <a
                    href="/api/catalogos/descargar_bitacora/"
                    download="bitacora_fotos.txt"
                    className="fotos-link-bitacora"
                  >
                    Descargar bitácora
                  </a>
                </div>
                {listaFotos.length === 0 ? (
                  <p className="fotos-lista-vacia">No hay fotos registradas aún.</p>
                ) : (
                  <table className="fotos-tabla">
                    <thead>
                      <tr>
                        <th>Archivo</th>
                        <th>Fecha</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {listaFotos.map((foto) => (
                        <tr key={foto.nombre}>
                          <td>{foto.nombre}</td>
                          <td>{foto.fecha}</td>
                          <td>
                            <a
                              href={`/api/catalogos/descargar_foto/${encodeURIComponent(foto.nombre)}/`}
                              download={foto.nombre}
                              className="fotos-link-dl"
                            >
                              ↓ Descargar
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
