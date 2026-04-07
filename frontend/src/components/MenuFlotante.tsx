import { useEffect, useRef, useState } from "react";

type MenuFlotanteProps = {
  myColor: string;
  myTexto: string;
};
function MenuFlotante({ myColor, myTexto }: MenuFlotanteProps) {
  const divRef = useRef<HTMLDivElement | null>(null);
  const [isSticky, setIsSticky] = useState(false);
  const [originalTop, setOriginalTop] = useState<number>(0);
  const [headerOffset, setHeaderOffset] = useState<number>(0);

  useEffect(() => {
    const header = document.getElementById("menu_header");
    const div = divRef.current;
    if (!header || !div) return;

    let observer: ResizeObserver;

    const rect = div.getBoundingClientRect();
    setOriginalTop(rect.top + window.scrollY);
    //setOriginalTop(rect.top);

    const calcularAlturaYTop = () => {
      const altura = header.offsetHeight || 0;
      setHeaderOffset(altura * 2);
    };

    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const top = originalTop;

      if (scrollTop + headerOffset >= top && !isSticky) {
        setIsSticky(true);
      } else if (scrollTop + headerOffset < top && isSticky) {
        setIsSticky(false);
      }
    };

    // Primer cálculo inmediato
    calcularAlturaYTop();

    // Esperar a que se carguen las imágenes dentro del header
    const imgs = header.getElementsByTagName("img");
    let cargadas = 0;
    for (let i = 0; i < imgs.length; i++) {
      if (imgs[i].complete) cargadas++;
      else {
        imgs[i].addEventListener("load", () => {
          cargadas++;
          if (cargadas === imgs.length) calcularAlturaYTop();
        });
      }
    }

    // Observar cambios de tamaño en el header
    observer = new ResizeObserver(() => calcularAlturaYTop());
    observer.observe(header);

    // Escuchar scroll
    window.addEventListener("scroll", handleScroll);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (observer) observer.disconnect();
    };
  }, [isSticky, originalTop, headerOffset]);

  return (
    <div
      ref={divRef}
      className={`${
        isSticky ? "position-fixed shadow bg-doradoIMSS w-100" : "bg-doradoIMSS"
      } transition-all`}
      style={{
        top: isSticky ? headerOffset : "auto",
        backgroundColor: myColor,
        transition: "top 0.6s ease-in-out",
        zIndex: 1000,
      }}
    >
      <div className="container py-3">
        <h4 className="texto-dinamico">{myTexto}</h4>
      </div>
    </div>
  );
}

export default MenuFlotante;
