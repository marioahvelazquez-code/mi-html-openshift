import Offcanvas from "react-bootstrap/Offcanvas";
import { FaFacebookF, FaTwitter, FaInstagram, FaYoutube } from "react-icons/fa";
import logoBlanco from "../assets/img/logo-gob-mx.png";
import dpti from "../assets/img/dpti.png";

type Props = {
  show: boolean;
  onHide: () => void;
};

export default function MenuLateral({ show, onHide }: Props) {
  return (
    <>
      <Offcanvas
        show={show}
        onHide={onHide}
        placement="start"
        style={{ backgroundColor: "#10312b", width: "300px" }}
      >
        <Offcanvas.Header closeButton closeVariant="white">
          <div className="d-flex align-items-center gap-3">
            <img
              src={dpti}
              className="img-fluid"
              style={{ maxHeight: "50px" }}
              alt="IMSS"
            />
          </div>
        </Offcanvas.Header>

        <Offcanvas.Body className="text-white d-flex flex-column justify-content-between h-100">
          <div>
            <h6 className="fw-bold">Explora</h6>
            <ul className="list-unstyled">
              <li>
                <a href="#" className="text-white text-decoration-none">
                  Tableros de Información
                </a>
              </li>
              <li>
                <a href="#" className="text-white text-decoration-none">
                  Informes
                </a>
              </li>
              <li>
                <a href="#" className="text-white text-decoration-none">
                  Descarga de Información
                </a>
              </li>
              <li>
                <a href="#" className="text-white text-decoration-none">
                  Información Histórica
                </a>
              </li>
            </ul>

            <h6 className="fw-bold mt-3">Consulta de Información</h6>
            <h6 className="fw-bold mt-3">Sobre DPTI</h6>
          </div>

          {/* ======= PIE DEL MENÚ ======= */}
          <div className="mt-4">
            <div className="w-50">
              <img className="img-fluid" src={logoBlanco} alt="Logo" />
            </div>

            <div className="mt-3 d-flex">
              <FaFacebookF
                size={20}
                className="me-3 gold-icon cursor-pointer"
              />
              <FaTwitter size={20} className="me-3 gold-icon cursor-pointer" />
              <FaInstagram
                size={20}
                className="me-3 gold-icon cursor-pointer"
              />
              <FaYoutube size={20} className="gold-icon cursor-pointer" />
            </div>
          </div>
        </Offcanvas.Body>
      </Offcanvas>
    </>
  );
}
