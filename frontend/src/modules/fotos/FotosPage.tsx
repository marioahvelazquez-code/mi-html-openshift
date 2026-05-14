
import { useState } from "react";
import "./fotos.css";

const preguntas = [
  {
    id: 1,
    texto: "¿Qué tan claro tienes cuál es el propósito del Modelo de Gestión Hospitalaria Humanista y de Trato Digno?",
    opciones: [
      "Totalmente claro",
      "Bastante claro",
      "Ni claro ni confuso",
      "Poco claro",
      "Nada claro",
    ],
  },
  {
    id: 2,
    texto: "La estructura y secuencia de los temas facilitaron el seguimiento de la presentación.",
    opciones: [
      "Totalmente de acuerdo",
      "De acuerdo",
      "Ni de acuerdo ni en desacuerdo",
      "En desacuerdo",
      "Totalmente en desacuerdo",
    ],
  },
  {
    id: 3,
    texto: "¿Consideras que el material comunica con éxito la relación entre los indicadores y la viabilidad financiera del Instituto?",
    opciones: [
      "Sí completamente",
      "En su mayoría",
      "No estoy seguro/a",
      "Solo parcialmente",
      "No",
    ],
  },
  {
    id: 4,
    texto: "¿Considera que la presentación cumplió adecuadamente con este propósito?",
    opciones: ["Sí", "No"],
  },
  {
    id: 5,
    texto: "¿Cómo calificarías el diseño visual y la organización de las diapositivas?",
    opciones: [
      "Excelente",
      "Bueno",
      "Ni bueno ni malo",
      "Regular",
      "Deficiente",
    ],
  },
  {
    id: 6,
    texto: "Las gráficas, indicadores y elementos visuales ayudaron a comprender el contenido.",
    opciones: [
      "Totalmente de acuerdo",
      "De acuerdo",
      "Ni de acuerdo ni en desacuerdo",
      "En desacuerdo",
      "Totalmente en desacuerdo",
    ],
  },
  {
    id: 7,
    texto: "La cantidad de información por diapositiva te pareció:",
    opciones: ["Adecuada", "Demasiada", "Insuficiente"],
  },
  {
    id: 8,
    texto: "El diseño y formato del material facilitaron la lectura y comprensión.",
    opciones: [
      "Totalmente de acuerdo",
      "De acuerdo",
      "Ni de acuerdo ni en desacuerdo",
      "En desacuerdo",
      "Totalmente en desacuerdo",
    ],
  },
  {
    id: 9,
    texto: "El material evitó el uso excesivo de tecnicismos que dificultaran la comprensión.",
    opciones: [
      "Totalmente de acuerdo",
      "De acuerdo",
      "Ni de acuerdo ni en desacuerdo",
      "En desacuerdo",
      "Totalmente en desacuerdo",
    ],
  },
  {
    id: 10,
    texto: "En general, ¿cómo calificarías la calidad de esta presentación como material de capacitación?",
    opciones: [
      "Excelente",
      "Bueno",
      "Ni bueno ni malo",
      "Regular",
      "Deficiente",
    ],
  },
  {
    id: 11,
    texto: "¿Existe algún indicador o variable relevante para la gestión hospitalaria que no haya sido contemplado en el Tablero?",
    opciones: ["Sí", "No"],
    campoAbierto: true,
  },
];

export default function FotosPage() {
  const [ooad, setOoad] = useState("");
  const [unidadMedica, setUnidadMedica] = useState("");
  const [cargo, setCargo] = useState("");
  const [respuestas, setRespuestas] = useState<{ [key: number]: string }>({});
  const [indicadoresExtra, setIndicadoresExtra] = useState("");
  const [error, setError] = useState("");
  const [guardadoExitoso, setGuardadoExitoso] = useState(false);
  const [modalGuardadoAbierto, setModalGuardadoAbierto] = useState(false);

  const limpiarFormulario = () => {
    setOoad("");
    setUnidadMedica("");
    setCargo("");
    setRespuestas({});
    setIndicadoresExtra("");
  };

  const manejarGuardar = async () => {
    // Validación: todas las preguntas respondidas
    // Validar campos de identificación
    if (!ooad.trim() || !unidadMedica.trim() || !cargo.trim()) {
      setError("Por favor completa los campos de OOAD, Unidad Médica de adscripción y Cargo.");
      return;
    }
    const faltantes = preguntas.filter((p) => {
      if (!respuestas[p.id]) return true;
      // Solo la última pregunta (id 11) requiere campo abierto si es "Sí"
      if (p.id === 11 && p.campoAbierto && respuestas[p.id] === "Sí" && !indicadoresExtra.trim()) return true;
      return false;
    });
    if (faltantes.length > 0) {
      setError("Por favor responde todas las preguntas obligatorias. Si respondes 'Sí' en la última pregunta, debes escribir tu sugerencia.");
      return;
    }
    setError("");
    setGuardadoExitoso(false);
    try {
      // Construir el payload para el backend con identificación y respuestas
      const payload = {
        delegacion: ooad,
        titular_unidad: unidadMedica,
        cargo_usuario: cargo,
        pregunta_1: respuestas[1] || "",
        pregunta_2: respuestas[2] || "",
        pregunta_3: respuestas[3] || "",
        pregunta_4: respuestas[4] || "",
        pregunta_5: respuestas[5] || "",
        pregunta_6: respuestas[6] || "",
        pregunta_7: respuestas[7] || "",
        pregunta_8: respuestas[8] || "",
        pregunta_9: respuestas[9] || "",
        pregunta_10: respuestas[10] || "",
        pregunta_11: respuestas[11] || "",
        sugerencia: indicadoresExtra || "",
      };

      const response = await fetch("/api/catalogos/guardar_inicio_operaciones/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setGuardadoExitoso(false);
        setError(data.message || "Error al guardar el registro.");
        return;
      }
      setGuardadoExitoso(true);
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
        <h3 className="fotos-title" style={{ textAlign: "center", marginBottom: 38 }}>Cuestionario de Evaluación</h3>
        <div className="fotos-form" style={{ marginTop: 10 }}>
          <div className="fotos-section" style={{ marginBottom: 18 }}>
            <div className="fotos-grid fotos-grid-2">
              <div className="fotos-field fotos-field-full">
                <label className="fotos-label" htmlFor="ooad"><b>OOAD:</b></label>
                <input
                  id="ooad"
                  className="fotos-select"
                  type="text"
                  value={ooad}
                  onChange={e => setOoad(e.target.value)}
                  placeholder="Nombre de la OOAD"
                  required
                />
              </div>
              <div className="fotos-field fotos-field-full">
                <label className="fotos-label" htmlFor="unidad-medica"><b>Unidad Médica de adscripción:</b></label>
                <input
                  id="unidad-medica"
                  className="fotos-select"
                  type="text"
                  value={unidadMedica}
                  onChange={e => setUnidadMedica(e.target.value)}
                  placeholder="Nombre de la unidad médica"
                  required
                />
              </div>
              <div className="fotos-field fotos-field-full">
                <label className="fotos-label" htmlFor="cargo"><b>Cargo:</b></label>
                <input
                  id="cargo"
                  className="fotos-select"
                  type="text"
                  value={cargo}
                  onChange={e => setCargo(e.target.value)}
                  placeholder="Cargo del participante"
                  required
                />
              </div>
            </div>
          </div>
          <div style={{ margin: '0 0 24px 0', fontWeight: 600, fontSize: '1.1rem', color: '#fff', textAlign: 'left' }}>
            Selecciona la opción que mejor refleje tu opinión. Tu retroalimentación es valiosa y nos ayuda a mejorar el material.
          </div>
          {Array.from({ length: Math.ceil(preguntas.length / 2) }, (_, i) => (
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }} key={i}>
              {[preguntas[i * 2], preguntas[i * 2 + 1]].map(
                (pregunta) =>
                  pregunta && (
                    <div className="fotos-section" style={{ flex: 1, minWidth: 320, maxWidth: 500, marginBottom: 0 }} key={pregunta.id}>
                      <label className="fotos-label" style={{ fontWeight: 600 }}>{pregunta.id}. {pregunta.texto}</label>
                      <div style={{ height: 12 }} />
                      <div className="fotos-grid fotos-grid-2">
                        {pregunta.opciones.map((opcion) => (
                          <label key={opcion} className="fotos-radio-label" style={{ marginBottom: 3, display: "flex", alignItems: "center" }}>
                            <input
                              type="radio"
                              name={`pregunta-${pregunta.id}`}
                              value={opcion}
                              checked={respuestas[pregunta.id] === opcion}
                              onChange={() => setRespuestas({ ...respuestas, [pregunta.id]: opcion })}
                              required
                              style={{ marginRight: 6 }}
                            />
                            {opcion}
                          </label>
                        ))}
                      </div>
                      {pregunta.campoAbierto && pregunta.id === 11 && respuestas[pregunta.id] === "Sí" && (
                        <div className="fotos-field fotos-field-full" style={{ marginTop: 8 }}>
                          <label htmlFor="indicadores-extra" className="fotos-label">¿Cuál o cuáles indicadores sugerirías?</label>
                          <textarea
                            id="indicadores-extra"
                            className="fotos-select"
                            value={indicadoresExtra}
                            onChange={(e) => setIndicadoresExtra(e.target.value)}
                            placeholder="Escribe aquí tus sugerencias"
                            required
                          />
                        </div>
                      )}
                    </div>
                  )
              )}
            </div>
          ))}

          {error && <p className="fotos-error">{error}</p>}

          <div className="fotos-actions">
            <button
              type="button"
              className={`fotos-btn ${guardadoExitoso ? "fotos-btn-ok" : ""}`}
              onClick={manejarGuardar}
            >
              {guardadoExitoso ? "Guardado" : "Enviar"}
            </button>
          </div>
        </div>
      </div>

      {modalGuardadoAbierto && (
        <div className="revision-modal-overlay" onClick={cerrarModalGuardado}>
          <div className="revision-modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="revision-modal-badge revision-modal-success">Completado</div>
            <h3 className="revision-modal-title">Respuestas enviadas</h3>
            <p className="revision-modal-message">
              ¡Gracias por tu participación!
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
