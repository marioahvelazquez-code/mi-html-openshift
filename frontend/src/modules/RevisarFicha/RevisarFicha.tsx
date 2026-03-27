
import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";
import "../../assets/css/estilos.css";

const pdfModules = import.meta.glob("./Fichas_estatales/*.pdf", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const pptModules = import.meta.glob("./Fichas_estatales/*.{ppt,pptx,PPT,PPTX}", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const normalizarClave = (valor: string) =>
  valor
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");

const extraerNombreEntidad = (item: unknown): string | null => {
  if (typeof item === "string") {
    const nombre = item.trim();
    return nombre.length > 0 ? nombre : null;
  }

  if (item && typeof item === "object" && "nombre" in item) {
    const nombre = (item as { nombre?: unknown }).nombre;
    if (typeof nombre === "string") {
      const limpio = nombre.trim();
      return limpio.length > 0 ? limpio : null;
    }
  }

  return null;
};

const obtenerPdfPorEntidad = (entidad: string) => {
  if (entidad === "Aguascalientes") return pdfModules["./Fichas_estatales/Ficha_Estatal_AGUASCALIENTES.pdf"] ?? null;
  if (entidad === "Baja California") return pdfModules["./Fichas_estatales/Ficha_Estatal_BAJA CALIFORNIA.pdf"] ?? null;
  if (entidad === "Baja California Sur") return pdfModules["./Fichas_estatales/Ficha_Estatal_BAJA CALIFORNIA SUR.pdf"] ?? null;
  if (entidad === "Campeche") return pdfModules["./Fichas_estatales/Ficha_Estatal_CAMPECHE.pdf"] ?? null;
  if (entidad === "Coahuila") return pdfModules["./Fichas_estatales/Ficha_Estatal_COAHUILA.pdf"] ?? null;
  if (entidad === "Colima") return pdfModules["./Fichas_estatales/Ficha_Estatal_COLIMA.pdf"] ?? null;
  if (entidad === "Chiapas") return pdfModules["./Fichas_estatales/Ficha_Estatal_CHIAPAS.pdf"] ?? null;
  if (entidad === "Chihuahua") return pdfModules["./Fichas_estatales/Ficha_Estatal_CHIHUAHUA.pdf"] ?? null;
  if (entidad === "Ciudad de México") return pdfModules["./Fichas_estatales/Ficha_Estatal_CIUDAD DE MÉXICO.pdf"] ?? null;
  if (entidad === "Durango") return pdfModules["./Fichas_estatales/Ficha_Estatal_DURANGO.pdf"] ?? null;
  if (entidad === "Guanajuato") return pdfModules["./Fichas_estatales/Ficha_Estatal_GUANAJUATO.pdf"] ?? null;
  if (entidad === "Guerrero") return pdfModules["./Fichas_estatales/Ficha_Estatal_GUERRERO.pdf"] ?? null;
  if (entidad === "Hidalgo") return pdfModules["./Fichas_estatales/Ficha_Estatal_HIDALGO.pdf"] ?? null;
  if (entidad === "Jalisco") return pdfModules["./Fichas_estatales/Ficha_Estatal_JALISCO.pdf"] ?? null;
  if (entidad === "Estado de México") return pdfModules["./Fichas_estatales/Ficha_Estatal_ESTADO DE MÉXICO.pdf"] ?? null;
  if (entidad === "Michoacán") return pdfModules["./Fichas_estatales/Ficha_Estatal_MICHOACÁN.pdf"] ?? null;
  if (entidad === "Morelos") return pdfModules["./Fichas_estatales/Ficha_Estatal_MORELOS.pdf"] ?? null;
  if (entidad === "Nayarit") return pdfModules["./Fichas_estatales/Ficha_Estatal_NAYARIT.pdf"] ?? null;
  if (entidad === "Nuevo León") return pdfModules["./Fichas_estatales/Ficha_Estatal_NUEVO LEÓN.pdf"] ?? null;
  if (entidad === "Oaxaca") return pdfModules["./Fichas_estatales/Ficha_Estatal_OAXACA.pdf"] ?? null;
  if (entidad === "Puebla") return pdfModules["./Fichas_estatales/Ficha_Estatal_PUEBLA.pdf"] ?? null;
  if (entidad === "Querétaro") return pdfModules["./Fichas_estatales/Ficha_Estatal_QUERÉTARO.pdf"] ?? null;
  if (entidad === "Quintana Roo") return pdfModules["./Fichas_estatales/Ficha_Estatal_QUINTANA ROO.pdf"] ?? null;
  if (entidad === "San Luis Potosí") return pdfModules["./Fichas_estatales/Ficha_Estatal_SAN LUIS POTOSÍ.pdf"] ?? null;
  if (entidad === "Sinaloa") return pdfModules["./Fichas_estatales/Ficha_Estatal_SINALOA.pdf"] ?? null;
  if (entidad === "Sonora") return pdfModules["./Fichas_estatales/Ficha_Estatal_SONORA.pdf"] ?? null;
  if (entidad === "Tabasco") return pdfModules["./Fichas_estatales/Ficha_Estatal_TABASCO.pdf"] ?? null;
  if (entidad === "Tamaulipas") return pdfModules["./Fichas_estatales/Ficha_Estatal_TAMAULIPAS.pdf"] ?? null;
  if (entidad === "Tlaxcala") return pdfModules["./Fichas_estatales/Ficha_Estatal_TLAXCALA.pdf"] ?? null;
  if (entidad === "Veracruz") return pdfModules["./Fichas_estatales/Ficha_Estatal_VERACRUZ.pdf"] ?? null;
  if (entidad === "Yucatán") return pdfModules["./Fichas_estatales/Ficha_Estatal_YUCATÁN.pdf"] ?? null;
  if (entidad === "Zacatecas") return pdfModules["./Fichas_estatales/Ficha_Estatal_ZACATECAS.pdf"] ?? null;

  // Fallback: busca por coincidencia normalizada para evitar fallos por acentos/encoding.
  const claveEntidad = normalizarClave(entidad);
  const entradaEncontrada = Object.entries(pdfModules).find(([ruta]) => {
    const nombreArchivo = ruta.split("/").pop() ?? "";
    const entidadArchivo = nombreArchivo
      .replace("Ficha_Estatal_", "")
      .replace(".pdf", "");

    return normalizarClave(entidadArchivo) === claveEntidad;
  });

  if (entradaEncontrada) {
    return entradaEncontrada[1];
  }

  return null;
};

const obtenerPptPorEntidad = (entidad: string) => {
  const claveEntidad = normalizarClave(entidad);

  const entradaEncontrada = Object.entries(pptModules).find(([ruta]) => {
    const nombreArchivo = ruta.split("/").pop() ?? "";
    const baseSinExtension = nombreArchivo.replace(/\.(ppt|pptx)$/i, "");
    const baseNormalizada = normalizarClave(baseSinExtension);

    return baseNormalizada.includes(claveEntidad);
  });

  if (entradaEncontrada) {
    return entradaEncontrada[1];
  }

  return null;
};

// Worker de PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const ENTIDADES_FALLBACK = [
  "Aguascalientes","Baja California","Baja California Sur","Campeche","Coahuila","Colima","Chiapas","Chihuahua",
  "Ciudad de México","Durango","Guanajuato","Guerrero","Hidalgo","Jalisco","Estado de México","Michoacán","Morelos",
  "Nayarit","Nuevo León","Oaxaca","Puebla","Querétaro","Quintana Roo","San Luis Potosí","Sinaloa","Sonora","Tabasco",
  "Tamaulipas","Tlaxcala","Veracruz","Yucatán","Zacatecas"
];

const hospitalesPorEntidad: Record<string, string[]> = {
  Aguascalientes: [], "Baja California": [], "Baja California Sur": [], Campeche: [], Coahuila: [], Colima: [],
  Chiapas: [], Chihuahua: [], "Ciudad de México": [], Durango: [], Guanajuato: [], Guerrero: [], Hidalgo: [],
  Jalisco: [], "Estado de México": [], Michoacán: [], Morelos: [], Nayarit: [], "Nuevo León": [], Oaxaca: [],
  Puebla: [], Querétaro: [], "Quintana Roo": [], "San Luis Potosí": [], Sinaloa: [], Sonora: [], Tabasco: [],
  Tamaulipas: [], Tlaxcala: [], Veracruz: [], Yucatán: [], Zacatecas: [],
};

type TipoFicha = "estatal" | "hospitalaria";
type EstatusRevision = "" | "correcta" | "correccion";

interface RevisionPorPagina {
  estatus: EstatusRevision;
  comentario: string;
}

interface ItemBitacora {
  pagina?: number;
  estatus?: string;
  comentario?: string;
}

const clonarRevisiones = (items: RevisionPorPagina[]) =>
  items.map((item) => ({
    estatus: item.estatus,
    comentario: item.comentario,
  }));

export default function RevisarFicha() {

  const [numPages, setNumPages] = useState(0);
  const [paginaActual, setPaginaActual] = useState(1);
  const [entidadSeleccionada, setEntidadSeleccionada] = useState("Aguascalientes");
  const [entidades, setEntidades] = useState<string[]>(ENTIDADES_FALLBACK);
  const [tipoFicha, setTipoFicha] = useState<TipoFicha>("estatal");
  const [hospitalSeleccionado, setHospitalSeleccionado] = useState("");
  const [revisiones, setRevisiones] = useState<RevisionPorPagina[]>([]);
  const [revisionesBase, setRevisionesBase] = useState<RevisionPorPagina[]>([]);
  const [modalRevision, setModalRevision] = useState<{
    abierto: boolean;
    titulo: string;
    mensaje: string;
    tipo: "info" | "warning" | "success";
  }>({
    abierto: false,
    titulo: "",
    mensaje: "",
    tipo: "info",
  });

  const visorPdfRef = useRef<HTMLDivElement | null>(null);
  const [pdfWidth, setPdfWidth] = useState(900);

  const hospitalesDisponibles = hospitalesPorEntidad[entidadSeleccionada] || [];

  const pdfSeleccionado =
    tipoFicha === "estatal"
      ? obtenerPdfPorEntidad(entidadSeleccionada)
      : null;

  const pptSeleccionado =
    tipoFicha === "estatal"
      ? obtenerPptPorEntidad(entidadSeleccionada)
      : null;

  useEffect(() => {
    let isMounted = true;

    const cargarEntidades = async () => {
      try {
        const res = await fetch("/api/catalogos/entidades/");
        if (!res.ok) return;

        const payload: unknown = await res.json();
        if (!Array.isArray(payload)) return;

        const nombres = payload
          .map(extraerNombreEntidad)
          .filter((nombre): nombre is string => Boolean(nombre));

        if (!isMounted || nombres.length === 0) return;

        setEntidades(nombres);
        setEntidadSeleccionada((prev) =>
          nombres.includes(prev) ? prev : nombres[0],
        );
      } catch {
        // Si falla API, se mantiene el fallback local.
      }
    };

    cargarEntidades();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {

    const contenedor = visorPdfRef.current;
    if (!contenedor) return;

    const actualizarAncho = () => {
      const anchoDisponible = contenedor.clientWidth;
      const anchoFinal = Math.max(300, anchoDisponible - 24);
      setPdfWidth(anchoFinal);
    };

    actualizarAncho();

    const resizeObserver = new ResizeObserver(() => {
      actualizarAncho();
    });

    resizeObserver.observe(contenedor);
    window.addEventListener("resize", actualizarAncho);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", actualizarAncho);
    };

  }, []);

  // #Mario: Inicio helper base de objeto para bitacora.
  const obtenerBaseObjeto = () => {
    const nombrePdf = (pdfSeleccionado?.split("/").pop() ?? `Ficha_Estatal_${entidadSeleccionada}.pdf`)
      .replace(/\?.*$/, "");

    return nombrePdf.replace(/\.pdf$/i, "").replace(/\s+/g, "_");
  };
  // #Mario: Fin helper base de objeto para bitacora.

  // #Mario: Inicio carga de revisiones guardadas por entidad.
  const cargarRevisionesGuardadas = async (totalPaginas: number) => {
    const vacias: RevisionPorPagina[] = Array.from({ length: totalPaginas }, () => ({
      estatus: "",
      comentario: "",
    }));

    if (!pdfSeleccionado || totalPaginas <= 0) {
      setRevisiones(clonarRevisiones(vacias));
      setRevisionesBase(clonarRevisiones(vacias));
      return;
    }

    try {
      const res = await fetch(
        `/api/catalogos/bitacora/?id_presentacion=${encodeURIComponent(tipoFicha)}&id_objeto_base=${encodeURIComponent(obtenerBaseObjeto())}`,
      );

      if (!res.ok) {
        setRevisiones(clonarRevisiones(vacias));
        setRevisionesBase(clonarRevisiones(vacias));
        return;
      }

      const data: unknown = await res.json();
      const items = (data && typeof data === "object" && Array.isArray((data as { items?: unknown }).items)
        ? (data as { items: unknown[] }).items
        : []) as ItemBitacora[];

      for (const item of items) {
        const pagina = Number(item.pagina);
        if (!Number.isInteger(pagina) || pagina < 1 || pagina > totalPaginas) continue;

        const estatusRaw = String(item.estatus || "").trim().toLowerCase();
        const estatus: EstatusRevision =
          estatusRaw === "aprobado"
            ? "correcta"
            : estatusRaw === "requiere corrección" || estatusRaw === "requiere correccion"
            ? "correccion"
            : "";

        vacias[pagina - 1] = {
          estatus,
          comentario: String(item.comentario || ""),
        };
      }

      setRevisiones(clonarRevisiones(vacias));
      setRevisionesBase(clonarRevisiones(vacias));
    } catch {
      setRevisiones(clonarRevisiones(vacias));
      setRevisionesBase(clonarRevisiones(vacias));
    }
  };
  // #Mario: Fin carga de revisiones guardadas por entidad.

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPaginaActual(1);

    void cargarRevisionesGuardadas(numPages);
  };

  // #Mario: Inicio manejo de error de carga PDF.
  const onDocumentLoadError = () => {
    setNumPages(0);
    abrirModalRevision(
      "Error al cargar la ficha",
      "No se pudo cargar el PDF seleccionado.",
      "warning",
    );
  };
  // #Mario: Fin manejo de error de carga PDF.

  const siguiente = () => {
    if (paginaActual < numPages) setPaginaActual(paginaActual + 1);
  };

  const anterior = () => {
    if (paginaActual > 1) setPaginaActual(paginaActual - 1);
  };

  const cambiarEstatus = (estatus: EstatusRevision) => {

    const copia = [...revisiones];
    if (!copia[paginaActual - 1]) return;

    copia[paginaActual - 1] = {
      ...copia[paginaActual - 1],
      estatus,
    };

    if (estatus === "correcta") {
      copia[paginaActual - 1] = {
        ...copia[paginaActual - 1],
        comentario: "",
      };
    }

    setRevisiones(copia);
  };

  const cambiarComentario = (texto: string) => {

    const copia = [...revisiones];
    if (!copia[paginaActual - 1]) return;

    copia[paginaActual - 1] = {
      ...copia[paginaActual - 1],
      comentario: texto,
    };
    setRevisiones(copia);
  };

  // #Mario: Inicio helpers de modal de finalizacion.
  const abrirModalRevision = (
    titulo: string,
    mensaje: string,
    tipo: "info" | "warning" | "success" = "info",
  ) => {
    setModalRevision({
      abierto: true,
      titulo,
      mensaje,
      tipo,
    });
  };

  const cerrarModalRevision = () => {
    setModalRevision((prev) => ({
      ...prev,
      abierto: false,
    }));
  };
  // #Mario: Fin helpers de modal de finalizacion.

  // #Mario: Inicio guardado de revision de paginas revisadas.
  const guardarRevisionPagina = async () => {
    if (!pdfSeleccionado) return;

    const revisionesGuardables = revisiones
      .map((revision, index) => ({
        pagina: index + 1,
        revision,
        revisionBase: revisionesBase[index] || { estatus: "", comentario: "" },
      }))
      .filter(({ revision, revisionBase }) => {
        const revisada = revision.estatus === "correcta" || revision.estatus === "correccion";
        if (!revisada) {
          return false;
        }

        return (
          revision.estatus !== revisionBase.estatus ||
          (revision.comentario || "") !== (revisionBase.comentario || "")
        );
      });

    if (revisionesGuardables.length === 0) {
      abrirModalRevision("Sin cambios", "No hay cambios nuevos por guardar.", "info");
      return;
    }

    try {
      for (const { pagina, revision } of revisionesGuardables) {
        const estatusTexto =
          revision.estatus === "correcta"
            ? "Aprobado"
            : "Requiere corrección";

        const payload = {
          id: "010101",
          id_user: "311095917",
          id_presentacion: tipoFicha,
          id_objeto: `${obtenerBaseObjeto()}_${pagina}`,
          comentario: revision.comentario || "",
          estatus: estatusTexto,
        };

        const res = await fetch("/api/catalogos/bitacora/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          const message =
            typeof data?.message === "string"
              ? data.message
              : `No se pudo guardar la página ${pagina} en bitácora.`;
          abrirModalRevision("No se pudo guardar", message, "warning");
          return;
        }
      }

      setRevisionesBase(clonarRevisiones(revisiones));

      abrirModalRevision(
        "Guardado exitoso",
        `Se guardaron ${revisionesGuardables.length} páginas modificadas correctamente.`,
        "success",
      );
    } catch {
      abrirModalRevision("Error de conexión", "Error de conexión al guardar la revisión.", "warning");
    }
  };
  // #Mario: Fin guardado de revision de paginas revisadas.

  const descargarPPT = () => {
    if (!pptSeleccionado) return;

    const enlace = document.createElement("a");
    enlace.href = pptSeleccionado;

    const extension = pptSeleccionado.toLowerCase().includes(".pptx")
      ? ".pptx"
      : ".ppt";
    enlace.download = `Ficha_Estatal_${entidadSeleccionada}${extension}`;
    enlace.click();
  };

  // #Mario: Inicio accion finalizar revision.
  const finalizarRevision = async () => {
    if (!pdfSeleccionado || numPages <= 0) {
      abrirModalRevision("Sin ficha cargada", "No hay una ficha cargada para finalizar revisión.", "warning");
      return;
    }

    const paginasFaltantes: number[] = [];

    for (let pagina = 1; pagina <= numPages; pagina += 1) {
      const revisionPagina = revisiones[pagina - 1];
      const revisada =
        revisionPagina?.estatus === "correcta" ||
        revisionPagina?.estatus === "correccion";

      if (!revisada) {
        paginasFaltantes.push(pagina);
      }
    }

    if (paginasFaltantes.length > 0) {
      abrirModalRevision(
        "Páginas pendientes",
        `Faltan por revisar las páginas: ${paginasFaltantes.join(", ")}`,
        "warning",
      );
      return;
    }

    const payload = {
      id_user: "311095917",
      id_presentacion: tipoFicha,
      id_objeto_base: obtenerBaseObjeto(),
      revisiones,
    };

    try {
      const res = await fetch("/api/catalogos/bitacora/reporte-excel/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const message =
          typeof data?.message === "string"
            ? data.message
            : "No se pudo generar el reporte en Excel.";
        abrirModalRevision("No se pudo finalizar", message, "warning");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `reporte_revision_${obtenerBaseObjeto()}.xls`;
      enlace.click();
      URL.revokeObjectURL(url);

      abrirModalRevision(
        "Revisión finalizada",
        "Todas las páginas están revisadas. Se generó el reporte en Excel.",
        "success",
      );
    } catch {
      abrirModalRevision("Error de conexión", "Error de conexión al generar el reporte en Excel.", "warning");
    }
  };
  // #Mario: Fin accion finalizar revision.

  const revisionActual =
    revisiones[paginaActual - 1] || { estatus: "", comentario: "" };

  // #Mario: Inicio valores visuales del paginador.
  const totalPaginasVisual = Math.max(numPages, revisiones.length, revisionesBase.length);
  const paginaActualVisual =
    pdfSeleccionado && totalPaginasVisual > 0
      ? Math.max(1, Math.min(paginaActual, totalPaginasVisual))
      : 0;
  const paginadorCargando = Boolean(pdfSeleccionado) && totalPaginasVisual === 0;
  // #Mario: Fin valores visuales del paginador.

  // #Mario: Inicio estado visual de revisión por página.
  const paginaRevisada = revisionActual.estatus === "correcta" || revisionActual.estatus === "correccion";
  // #Mario: Fin estado visual de revisión por página.

  const limpiarRevision = () => {
    setPaginaActual(1);
    setNumPages(0);
    setRevisiones([]);
  };

  return (

    <div className="container-fluid py-4">

      <div className="row align-items-start">

        {/* IZQUIERDA */}
        <div className="col-md-6 d-flex flex-column align-items-center ps-5">

          <div className="d-flex justify-content-center gap-4 mb-3">

            <button className="btn-custom" onClick={anterior} disabled={!pdfSeleccionado}>
              <ChevronLeft size={18} className="me-2" />
              Anterior
            </button>

            <button className="btn-custom" onClick={siguiente} disabled={!pdfSeleccionado}>
              Siguiente
              <ChevronRight size={18} className="ms-1" />
            </button>

          </div>

          <div className="visor-pdf" ref={visorPdfRef}>

            {tipoFicha === "hospitalaria" ? (
              <div className="text-center w-100 py-5">
                Seleccione un hospital cuando se cargue el catálogo correspondiente.
              </div>
            ) : pdfSeleccionado ? (

              <Document
                key={`${entidadSeleccionada}-${pdfSeleccionado ?? "sin-pdf"}`}
                file={pdfSeleccionado}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
              >

                <Page
                  pageNumber={paginaActual}
                  width={pdfWidth}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                />

              </Document>

            ) : (
              <div className="text-center w-100 py-5">
                No se encontró la ficha estatal de la entidad seleccionada.
              </div>
            )}

          </div>

          <div className="mt-3 d-flex justify-content-center align-items-center gap-5 w-100" style={{ maxWidth: "520px" }}>
            <button
              className="btn-custom"
              onClick={descargarPPT}
              disabled={!pptSeleccionado || tipoFicha === "hospitalaria"}
            >
              Descargar
            </button>

            <div className="fw-bold text-white px-3 py-1 rounded" style={{ backgroundColor: "rgba(0, 0, 0, 0.35)" }}>
              {paginadorCargando
                ? "Cargando páginas..."
                : `Página ${paginaActualVisual} de ${totalPaginasVisual}`}
            </div>
          </div>

        </div>

        {/* DERECHA */}
        <div className="col-md-4 d-flex flex-column align-items-center pt-2">

          <div className="w-100" style={{ maxWidth: "420px" }}>

            <div className="mb-4">

              <label className="form-label fw-bold text-white fs-4 text-center d-block">
                Seleccionar Entidad
              </label>

              <div className="select-wrapper">
                <select
                  className="select-custom"
                  value={entidadSeleccionada}
                  onChange={(e) => {
                    setEntidadSeleccionada(e.target.value);
                    setHospitalSeleccionado("");
                    limpiarRevision();
                  }}
                >
                  {entidades.map((entidad) => (
                    <option key={entidad} value={entidad}>
                      {entidad}
                    </option>
                  ))}
                </select>
              </div>

            </div>

            <div className="mb-4">
              <div className="d-flex justify-content-between gap-4">

                <label className="form-check-label text-white fw-semibold text-center flex-fill">
                  <div className="mb-2">Ficha Estatal</div>
                  <input
                    type="radio"
                    name="tipoFicha"
                    className="form-check-input"
                    checked={tipoFicha === "estatal"}
                    onChange={() => {
                      setTipoFicha("estatal");
                      setHospitalSeleccionado("");
                      limpiarRevision();
                    }}
                  />
                </label>

                <label className="form-check-label text-white fw-semibold text-center flex-fill">
                  <div className="mb-2">Ficha Hospitalaria</div>
                  <input
                    type="radio"
                    name="tipoFicha"
                    className="form-check-input"
                    checked={tipoFicha === "hospitalaria"}
                    onChange={() => {
                      setTipoFicha("hospitalaria");
                      limpiarRevision();
                    }}
                  />
                </label>

              </div>
            </div>

            <div className="mb-4">

              <div className="select-wrapper">
                <select
                  className="select-custom"
                  value={hospitalSeleccionado}
                  onChange={(e) => setHospitalSeleccionado(e.target.value)}
                  disabled={tipoFicha !== "hospitalaria"}
                >
                  <option value="">
                    {tipoFicha === "hospitalaria"
                      ? "Seleccione un hospital"
                      : "Disponible al elegir ficha hospitalaria"}
                  </option>
                  {hospitalesDisponibles.map((hospital) => (
                    <option key={hospital} value={hospital}>
                      {hospital}
                    </option>
                  ))}
                </select>
              </div>

            </div>

            <div className="mt-5">

              <label className="form-label fw-bold text-white fs-4 mb-4 text-center d-block">
                Revisión de ficha
              </label>

              <div className="d-flex justify-content-around mb-4">

                <label className="form-check-label text-white fw-semibold text-center">
                  <div className="mb-2">Aprobado</div>
                  <input
                    type="radio"
                    name={`estatus-${paginaActual}`}
                    className="form-check-input"
                    checked={revisionActual.estatus === "correcta"}
                    onChange={() => cambiarEstatus("correcta")}
                    disabled={tipoFicha === "hospitalaria" || !pdfSeleccionado}
                  />
                </label>

                <label className="form-check-label text-white fw-semibold text-center">
                  <div className="mb-2">Requiere corrección</div>
                  <input
                    type="radio"
                    name={`estatus-${paginaActual}`}
                    className="form-check-input"
                    checked={revisionActual.estatus === "correccion"}
                    onChange={() => cambiarEstatus("correccion")}
                    disabled={tipoFicha === "hospitalaria" || !pdfSeleccionado}
                  />
                </label>

              </div>

              <div className="mb-3">

              {/* #Mario: Inicio indicador visual de página revisada. */}
              <div className="d-flex justify-content-between align-items-center mb-3">
                <label className="form-label fw-bold text-white fs-4 mb-0 text-left d-block">
                  Comentarios
                </label>

                <span
                  className={`badge ${paginaRevisada ? "bg-success" : "bg-warning text-dark"}`}
                  style={{ fontSize: "0.9rem" }}
                >
                  {paginaRevisada ? "Página revisada" : "Falta por revisar"}
                </span>
              </div>
              {/* #Mario: Fin indicador visual de página revisada. */}

                <textarea
                  className="input-custom"
                  rows={6}
                  placeholder="Escribe aquí tus comentarios..."
                  disabled={
                    tipoFicha === "hospitalaria" ||
                    !pdfSeleccionado ||
                    revisionActual.estatus !== "correccion"
                  }
                  value={revisionActual.comentario}
                  onChange={(e) => cambiarComentario(e.target.value)}
                  style={{
                    resize: "none",
                    borderRadius: "16px",
                  }}
                />

              </div>

              <div className="d-flex justify-content-center gap-3 mt-4">

                <button
                  className="btn-custom"
                  onClick={guardarRevisionPagina}
                  disabled={tipoFicha === "hospitalaria" || !pdfSeleccionado}
                >
                  Guardar revisión
                </button>

                <button
                  className="btn-custom"
                  onClick={finalizarRevision}
                  disabled={tipoFicha === "hospitalaria" || !pdfSeleccionado}
                >
                  Finalizar revisión
                </button>

              </div>

            </div>

          </div>

        </div>

      </div>

      {modalRevision.abierto && (
        <div className="revision-modal-overlay" onClick={cerrarModalRevision}>
          <div
            className="revision-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`revision-modal-badge revision-modal-${modalRevision.tipo}`}>
              {modalRevision.tipo === "success"
                ? "Completado"
                : modalRevision.tipo === "warning"
                ? "Atención"
                : "Información"}
            </div>

            <h3 className="revision-modal-title">{modalRevision.titulo}</h3>
            <p className="revision-modal-message">{modalRevision.mensaje}</p>

            <div className="d-flex justify-content-center mt-4">
              <button className="btn-custom" onClick={cerrarModalRevision}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

    </div>

  );
}