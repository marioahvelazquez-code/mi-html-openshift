import { useEffect, useState } from "react";
import { MoreVertical } from "lucide-react";
import dpti from "../assets/img/dpti.png";

type Props = {
  onOpenMenu: () => void;
};
function MenuSuperior({ onOpenMenu }: Props) {
  const [visible, setVisible] = useState(false);
  const [headerOffset, setHeaderOffset] = useState(0);

  useEffect(() => {
    const header = document.getElementById("menu_principal");
    if (!header) return;

    // Calcula altura cuando las imágenes hayan cargado
    const calcularAltura = () => {
      const altura = header.offsetHeight || 0;
      setHeaderOffset(altura);
    };

    calcularAltura(); // primer intento inmediato

    // Segundo intento: cuando las imágenes se hayan cargado
    const imgs = header.getElementsByTagName("img");
    let cargadas = 0;
    for (let i = 0; i < imgs.length; i++) {
      if (imgs[i].complete) cargadas++;
      else
        imgs[i].addEventListener("load", () => {
          cargadas++;
          if (cargadas === imgs.length) calcularAltura();
        });
    }

    // También usamos ResizeObserver por si cambia luego
    const observer = new ResizeObserver(() => calcularAltura());
    observer.observe(header);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const manejarScroll = () => {
      setVisible(window.scrollY > 50);
    };
    window.addEventListener("scroll", manejarScroll);
    return () => window.removeEventListener("scroll", manejarScroll);
  }, []);

  return (
    <div
      id="menu_header"
      style={{
        opacity: visible ? 1 : 0,
        transition: "opacity 0.6s ease-in-out",
        backgroundColor: "#10312b",
        color: "#fff",
        padding: "1rem",
        position: "fixed",
        top: `${headerOffset}px`,
        left: 0,
        width: "100%",
        height: `${headerOffset}px`,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        gap: "0.5rem", // espacio entre botón e imagen
        overflow: "hidden", // evita que se desborde
      }}
    >
      <button
        className="btn btn-outline-light"
        type="button"
        onClick={onOpenMenu}
      >
        <MoreVertical size={24} />
      </button>
      <img className="img-fluid logo-chico" src={dpti} />
    </div>
  );
}

export default MenuSuperior;
