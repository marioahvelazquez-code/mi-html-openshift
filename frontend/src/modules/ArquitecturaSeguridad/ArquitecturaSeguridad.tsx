import "./ArquitecturaSeguridad.css";
import "../../assets/css/estilos.css";
import { useState } from "react";

const ArquitecturaSeguridad = () => {
  const [selectedValues, setSelectedValues] = useState({
    0: "",
    1: "",
    2: "",
    3: "",
    4: "",
  });

  const [tableValues, setTableValues] = useState<{
    [key: number]: { [key: string]: string | number };
  }>({});

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

  const abrirModalRevision = (
    titulo: string,
    mensaje: string,
    tipo: "info" | "warning" | "success",
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

  const cleanOption = (text: string) => {
    return text.replace(/^\d+\)\s*|^\d+=\s*/, "").trim();
  };

  const handleGuardar = async (idx: number) => {
    const rowData = data[idx];
    const rowValues = tableValues[idx] || {};

    const dataToSave = {
      variable: rowData.variable,
      definicion: rowData.definicion,
      tipo: rowData.tipo,
      unidadMedicion: rowData.unidadMedicion,
      fuente: rowData.fuente,
      consistente: rowValues.consistente || "",
      disponible: rowValues.disponible || "",
      confidencial: rowValues.confidencial || "",
      sensible: rowValues.sensible || "",
      resumen: rowValues.resumen || "",
      observaciones: rowValues.observaciones || "",
    };

    try {
      const response = await fetch("/api/catalogos/guardar-fila/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(dataToSave),
      });

      if (response.ok) {
        abrirModalRevision("Guardado exitoso", "La fila se guardo correctamente.", "success");
      } else {
        const errorData = await response.json().catch(() => null);
        abrirModalRevision(
          "No se pudo guardar",
          errorData?.message || "Error al guardar la fila",
          "warning",
        );
      }
    } catch (error) {
      console.error("Error:", error);
      abrirModalRevision("Error de conexion", "Error de conexion al guardar la fila.", "warning");
    }
  };
  const data = [
    {
      variable: "Sexo",
      definicion: "Sexo referido por el paciente",
      tipo: "Cualitativa ordinal",
      unidadMedicion: "1)Masculino\n2)Femenino\n3)No especificado",
      fuente: "MOCE, PHEDS, SIMOIQX",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Edad",
      definicion: "Años de vida",
      tipo: "Cuantitativa discreta",
      unidadMedicion: "Numérica",
      fuente: "MOCE, PHEDS, SIMOIQX",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Diagnóstico Principal",
      definicion: "Clave CIE 10 del diagnóstico principal",
      tipo: "Cualitativa nominal",
      unidadMedicion: "Numérica",
      fuente: "MOCE",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Diagnóstico secundario",
      definicion: "Clave CIE 10 del diagnóstico secundario",
      tipo: "Cualitativa nominal",
      unidadMedicion: "Numérica",
      fuente: "MOCE",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Diagnóstico complementario",
      definicion: "Clave CIE 10 del diagnóstico complementario",
      tipo: "Cualitativa nominal",
      unidadMedicion: "Numérica",
      fuente: "MOCE",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Ingresos y Egresos",
      definicion:
        "Ingresos y egresos con dx de tiroidectomía y la especialidad que realizó los mismos",
      tipo: "Cualitativa ordinal",
      unidadMedicion:
        "1) Parcial (CIE 9: 06.2-06.3)\n2) Total (CIE-9: 06.4-06.5) 06.2)\n3) Lobectomía tiroidea unilateral 06.3) Otra tiroidectomía parcial 06.4) Tiroidectomía total 06.5) Tiroidectomía retroesternal",
      fuente: "INGRESOS, EGRESOS",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Procedimiento principal de la solicitud",
      definicion: "Clave CIE 10 del diagnóstico principal",
      tipo: "Cualitativa nominal",
      unidadMedicion: "Numérica",
      fuente: "MOCE, PHEDS, SIMOIQX",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
    {
      variable: "Intervención Quirúrgica Solicitada",
      definicion: "Clave CIE 9 MC del procedimiento quirúrgico principal",
      tipo: "Cualitativa nominal",
      unidadMedicion: "Numérica",
      fuente: "MOCE, PHEDS, SIMOIQX",
      consistente: "Si",
      disponible: 1,
      confidencial: 0,
      sensible: 0,
      resumen: 0,
    },
  ];

  const criteriosValidacion = [
    {
      criterio: "Consistente con objetivo",
      noSi: "No\nSi",
    },
    {
      criterio: "Disponible",
      noSi: "1= Completa\n2= Parcial\n3= No disponible\n0= No",
    },
    {
      criterio: "Confidencial",
      noSi: "0= No\n1= Si",
    },
    {
      criterio: "Sensible",
      noSi: "0= No\n1= Si",
    },
    {
      criterio: "Resumen",
      noSi: "Aceptable\nNo aceptable",
    },
  ];

  return (
    <div className="arquitectura-seguridad">
      <div className="header-section">
        <h1>Requerimiento de variable y criterios de validación de fiabilidad</h1>
      </div>

      <div className="content-wrapper">
        <div className="criterios-section">
          <h3>Criterios de Validación</h3>
          <div className="criterios-grid">
            {criteriosValidacion.map((item, idx) => (
              <div key={idx} className="criterio-card">
                <div className="criterio-titulo">{item.criterio}</div>
                <select
                  className="criterio-select"
                  value={selectedValues[idx as keyof typeof selectedValues] || ""}
                  onChange={(e) =>
                    setSelectedValues({
                      ...selectedValues,
                      [idx]: e.target.value,
                    })
                  }
                >
                  <option value="">Seleccionar...</option>
                  {item.noSi.split("\n").map((valor, i) => (
                    <option key={i} value={valor}>
                      {cleanOption(valor)}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        <div className="table-responsive">
          <table className="arquitectura-table">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Definicion operacional</th>
                <th>Tipo de variable</th>
                <th>Unidad de Medicion</th>
                <th>Fuente de informacion</th>
                <th className="header-pink">Consistente con objetivo</th>
                <th className="header-pink">Disponible</th>
                <th className="header-pink">Confidencial</th>
                <th className="header-pink">Sensible</th>
                <th className="header-pink">Resumen</th>
                <th>Observaciones</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr key={idx}>
                  <td className="bold">{row.variable}</td>
                  <td>{row.definicion}</td>
                  <td>{row.tipo}</td>
                  <td>
                    {row.unidadMedicion.split("\n").map((line, i) => (
                      <div key={i}>{line}</div>
                    ))}
                  </td>
                  <td>{row.fuente}</td>
                  <td className="cell-pink">
                    <select
                      className="table-select"
                      value={tableValues[idx]?.consistente || ""}
                      onChange={(e) =>
                        setTableValues({
                          ...tableValues,
                          [idx]: { ...tableValues[idx], consistente: e.target.value },
                        })
                      }
                    >
                      <option value="">-</option>
                      <option value="No">No</option>
                      <option value="Si">Si</option>
                    </select>
                  </td>
                  <td className="cell-pink numeric">
                    <select
                      className="table-select"
                      value={tableValues[idx]?.disponible || ""}
                      onChange={(e) =>
                        setTableValues({
                          ...tableValues,
                          [idx]: { ...tableValues[idx], disponible: e.target.value },
                        })
                      }
                    >
                      <option value="">-</option>
                      <option value="1">{cleanOption("1= Completa")}</option>
                      <option value="2">{cleanOption("2= Parcial")}</option>
                      <option value="3">{cleanOption("3= No disponible")}</option>
                      <option value="0">{cleanOption("0= No")}</option>
                    </select>
                  </td>
                  <td className="cell-pink numeric">
                    <select
                      className="table-select"
                      value={tableValues[idx]?.confidencial || ""}
                      onChange={(e) =>
                        setTableValues({
                          ...tableValues,
                          [idx]: { ...tableValues[idx], confidencial: e.target.value },
                        })
                      }
                    >
                      <option value="">-</option>
                      <option value="0">{cleanOption("0= No")}</option>
                      <option value="1">{cleanOption("1= Si")}</option>
                    </select>
                  </td>
                  <td className="cell-pink numeric">
                    <select
                      className="table-select"
                      value={tableValues[idx]?.sensible || ""}
                      onChange={(e) =>
                        setTableValues({
                          ...tableValues,
                          [idx]: { ...tableValues[idx], sensible: e.target.value },
                        })
                      }
                    >
                      <option value="">-</option>
                      <option value="0">{cleanOption("0= No")}</option>
                      <option value="1">{cleanOption("1= Si")}</option>
                    </select>
                  </td>
                  <td className="cell-pink numeric">
                    <select
                      className="table-select"
                      value={tableValues[idx]?.resumen || ""}
                      onChange={(e) =>
                        setTableValues({
                          ...tableValues,
                          [idx]: { ...tableValues[idx], resumen: e.target.value },
                        })
                      }
                    >
                      <option value="">-</option>
                      <option value="Aceptable">Aceptable</option>
                      <option value="No aceptable">No aceptable</option>
                    </select>
                  </td>
                  <td>
                    <textarea
                      className="observaciones-input"
                      value={tableValues[idx]?.observaciones || ""}
                      onChange={(e) =>
                        setTableValues({
                          ...tableValues,
                          [idx]: { ...tableValues[idx], observaciones: e.target.value },
                        })
                      }
                      placeholder="Escribir observaciones..."
                    />
                  </td>
                  <td>
                    <button
                      className="btn-guardar"
                      onClick={() => handleGuardar(idx)}
                    >
                      Guardar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {modalRevision.abierto && (
        <div className="revision-modal-overlay" onClick={cerrarModalRevision}>
          <div className="revision-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className={`revision-modal-badge revision-modal-${modalRevision.tipo}`}>
              {modalRevision.tipo === "success"
                ? "Completado"
                : modalRevision.tipo === "warning"
                  ? "Atencion"
                  : "Informacion"}
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
};

export default ArquitecturaSeguridad;
