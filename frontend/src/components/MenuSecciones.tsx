import React from "react";
import CardSeccion from "./CardSeccion";
import { Home, ClipboardList } from "lucide-react";
import logoAnalitico from "../assets/img/analitico.png";
import logoBD from "../assets/img/bd.png";

export const VISTAS = {
  MENU: "menu",
  EXCEL: "excel",
  DASHBOARD: "dashboard",
  CONSULTAS_SQL: "consultassql",
} as const;

export type VistaActiva = (typeof VISTAS)[keyof typeof VISTAS];

interface Props {
  onOpenCargaMenu: (vista: VistaActiva) => void;
}

const MenuSecciones: React.FC<Props> = ({ onOpenCargaMenu }) => {
  const secciones = [
    {
      imageUrl: logoAnalitico,
      icon: <Home size={28} color="#9F2241" />,
      title: "Carga de Información",
      description: "Información de Excel a SQL",
      onClick: () => onOpenCargaMenu(VISTAS.EXCEL),
    },
    {
      imageUrl: logoBD,
      icon: <ClipboardList size={28} color="#9F2241" />,
      title: "Consultas de Información",
      description: "Datos para reportes y análisis",
      onClick: () => onOpenCargaMenu(VISTAS.CONSULTAS_SQL),
    },
  ];

  return (
    <div className="container my-4">
      <div className="row g-4 justify-content-center">
        {secciones.map((sec, idx) => (
          <div className="col-12 col-sm-6 col-md-4 col-lg-3" key={idx}>
            <CardSeccion {...sec} />
          </div>
        ))}
      </div>
    </div>
  );
};

export default MenuSecciones;
