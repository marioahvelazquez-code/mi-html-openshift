import React, { useEffect, useState } from "react";
import { Progress } from "antd";
import {
  getAreas,
  getTemas,
  getDiccionario,
  subirExcel,
  obtenerHojas,
} from "./services";
import type { Area, Tema, DiccionarioCampo } from "./types";

const CargaExcel: React.FC = () => {
  const [areas, setAreas] = useState<Area[]>([]);
  const [temas, setTemas] = useState<Tema[]>([]);
  const [diccionario, setDiccionario] = useState<DiccionarioCampo[]>([]);

  const [idArea, setIdArea] = useState<number | "">("");
  const [idTema, setIdTema] = useState<number | "">("");

  const [archivo, setArchivo] = useState<File | null>(null);
  const [mensaje, setMensaje] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [progress, setProgress] = useState(0);
  const [hojas, setHojas] = useState<string[]>([]);
  const [hojaSeleccionada, setHojaSeleccionada] = useState<string>("");

  /* 🔹 Cargar áreas al montar */
  useEffect(() => {
    getAreas().then(setAreas);
  }, []);

  /* 🔹 Cambio de área */
  const onAreaChange = async (value: number | "") => {
    setIdArea(value);
    setIdTema("");
    setArchivo(null);
    setDiccionario([]);
    setMensaje("");

    if (value !== "") {
      const data = await getTemas(value);
      setTemas(data);
    } else {
      setTemas([]);
    }
  };

  /* 🔹 Cambio de tema */
  const onTemaChange = async (value: number | "") => {
    setIdTema(value);
    setArchivo(null);
    setMensaje("");

    if (value !== "") {
      const dic = await getDiccionario(value);
      setDiccionario(dic);
    } else {
      setDiccionario([]);
    }
  };

  /* 🔹 Envío del archivo */
  const onSubmit = () => {
    if (!archivo || !idTema) return;

    setIsLoading(true);
    setProgress(0);

    let value = 0;

    const interval = setInterval(() => {
      value += Math.random() * 15;
      if (value >= 90) value = 90;
      setProgress(Math.floor(value));
    }, 300);

    setTimeout(async () => {
      try {
        if (!hojaSeleccionada) {
          setMensaje("Seleccione una hoja del Excel");
          return;
        }
        const data = await subirExcel(idTema, archivo, hojaSeleccionada);

        clearInterval(interval);
        setProgress(100);

        setMensaje(`Archivo cargado con ${data.total_registros} registros`);
      } catch (err: any) {
        clearInterval(interval);

        if (err?.error === "Errores de validación") {
          const detalles = err.detalle
            ?.slice(0, 5)
            .map((e: any) => `Fila ${e.fila}: ${e.columna} - ${e.error}`)
            .join(" | ");

          setMensaje(`❌ ${err.total_errores} errores. ${detalles}`);
        } else if (err?.error) {
          setMensaje(`❌ ${err.error}`);
        } else {
          setMensaje("❌ Error al enviar el archivo");
        }
      } finally {
        setIsLoading(false);
      }
    }, 0);
  };

  return (
    <div className="container mt-4">
      <h3>Carga de Excel</h3>

      <div className="contenedor-formulario">
        {/* IZQUIERDA */}
        <div className="lado-izquierdo">
          {/* Área */}
          <div className="select-wrapper">
            <select
              className="select-custom"
              value={idArea}
              disabled={isLoading}
              onChange={(e) =>
                onAreaChange(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Seleccione área</option>
              {areas.map((a) => (
                <option key={a.id_area} value={a.id_area}>
                  {a.nombre}
                </option>
              ))}
            </select>
          </div>

          {/* Tema */}
          <div className="select-wrapper">
            <select
              className="select-custom"
              value={idTema}
              disabled={idArea === "" || isLoading}
              onChange={(e) =>
                onTemaChange(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Seleccione tema</option>
              {temas.map((t) => (
                <option key={t.id_tema} value={t.id_tema}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </div>

          {/* Archivo */}
          <input
            type="file"
            className="input-custom"
            accept=".xlsx,.xls"
            disabled={idTema === "" || isLoading}
            onChange={async (e) => {
              const file = e.target.files?.[0] || null;
              setArchivo(file);

              if (file) {
                try {
                  console.log("📂 Archivo seleccionado:", file.name);

                  const data = await obtenerHojas(file);

                  console.log("📑 Hojas recibidas:", data);

                  setHojas(data.hojas || []);
                } catch (error) {
                  console.error("❌ Error obteniendo hojas:", error);
                  setMensaje("Error al leer las hojas del Excel");
                }
              }
            }}
          />
          {hojas.length > 0 && (
            <div className="select-wrapper">
              <select
                className="select-custom"
                value={hojaSeleccionada}
                onChange={(e) => setHojaSeleccionada(e.target.value)}
              >
                <option value="">Seleccione hoja</option>
                {hojas.map((h, i) => (
                  <option key={i} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
          )}
          {/* Botón */}
          <button
            className="btn-custom"
            disabled={idTema === "" || isLoading}
            onClick={onSubmit}
          >
            Subir archivo
          </button>

          {/* Barra de progreso */}
          {isLoading && (
            <div style={{ marginTop: "1rem" }}>
              <p style={{ marginBottom: "0.5rem", fontSize: "0.9rem" }}>
                Procesando...
              </p>

              <Progress
                percent={progress}
                status="active"
                strokeColor="#00acae"
              />
            </div>
          )}

          {/* Mensaje */}
          {mensaje && <div className="bloque-info">{mensaje}</div>}
        </div>

        {/* DERECHA */}
        <div className="lado-derecho">
          {diccionario.length > 0 && (
            <div className="bloque-info">
              <strong>Columnas esperadas:</strong>
              <ul>
                {diccionario.map((c) => (
                  <li key={c.id_campo}>
                    {c.columna_excel}
                    {c.obligatorio && <strong> *</strong>}
                    <small className="text-muted"> ({c.tipo_dato})</small>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CargaExcel;
