import Offcanvas from "react-bootstrap/Offcanvas";
import {
  Columns4,
  LogOut,
} from "lucide-react";
import { FaFacebookF, FaTwitter, FaInstagram, FaYoutube } from "react-icons/fa";

export const VISTAS = {
  MENU: "menu",
  INICIO: "inicio",
  EXCEL: "excel",
  DASHBOARD: "dashboard",
  CONSULTAS_SQL: "consultassql",
  REVISAPPTX: "RevisaPPTx",
} as const;

export type VistaActiva = (typeof VISTAS)[keyof typeof VISTAS];

type Props = {
  show: boolean;
  onHide: () => void;
  onOpenCargaMenu: (vista: VistaActiva) => void;
  onLogout: () => void;
};

export default function MenuLateral({ show, onHide, onOpenCargaMenu, onLogout }: Props) {
  return (
    <Offcanvas
      show={show}
      onHide={onHide}
      placement="start"
      className="menu-lateral"
    >
      <Offcanvas.Body className="d-flex flex-column h-100 text-white">
        {/* AVATAR */}
        {/* <div className="text-center mb-4"> */}
        {/* <div className="avatar-menu"><User size={55} /></div> */}
        {/* </div> */}

        <hr className="menu-divider" />

        {/* OPCIONES */}
        <ul className="menu-items list-unstyled">
          <li
            className="menu-item"
            onClick={() => {
              onOpenCargaMenu(VISTAS.REVISAPPTX);
              onHide();
            }}
          >
            <Columns4 size={18} className="menu-icon" />
            <span>Revisar Fichas</span>
          </li>

          <li
            className="menu-item"
            onClick={() => {
              onLogout();
              onHide();
            }}
          >
            <LogOut size={18} className="menu-icon" />
            <span>Salir de sesion</span>
          </li>
        </ul>
        {/* ======= PIE DEL MENÚ ======= */}
        <div className="mt-auto">
          <div className="d-flex">
            <FaFacebookF size={20} className="me-3 gold-icon cursor-pointer" />
            <FaTwitter size={20} className="me-3 gold-icon cursor-pointer" />
            <FaInstagram size={20} className="me-3 gold-icon cursor-pointer" />
            <FaYoutube size={20} className="gold-icon cursor-pointer" />
          </div>
        </div>
      </Offcanvas.Body>
    </Offcanvas>
  );
}
