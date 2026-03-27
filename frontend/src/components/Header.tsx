import { Menu, X } from "lucide-react";

import logoBlanco from "../assets/img/logo-gob-mx.png";
import dpti from "../assets/img/dpti.png";

type Props = {
  onOpenMenu: () => void;
  showMenu: boolean;
};

export default function Header({ onOpenMenu, showMenu }: Props) {
  return (
    <>
      <div id="menu_principal" className="fixed-top bg-verdeIMSS py-2">
        <div className="container d-flex align-items-center">
          {/* LOGOS */}
          <div className="d-flex align-items-center gap-3">
            <img
              src={logoBlanco}
              className="img-fluid"
              style={{ maxHeight: "50px" }}
              alt="IMSS"
            />

            <div
              style={{ width: "1px", height: "35px", background: "white" }}
            />

            <img
              src={dpti}
              className="img-fluid"
              style={{ maxHeight: "45px" }}
              alt="DPTI"
            />
          </div>

          {/* ICONO MENÚ */}

          <div
            className="ms-auto text-white cursor-pointer menu-icon"
            onClick={onOpenMenu}
          >
            {showMenu ? <X size={32} /> : <Menu size={32} />}
          </div>
        </div>
      </div>
    </>
  );
}
