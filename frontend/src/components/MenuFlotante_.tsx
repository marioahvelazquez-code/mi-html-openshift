import { useEffect, useRef, useState } from "react";

function MenuFlotante() {
  const divRef = useRef<HTMLDivElement | null>(null);
  const [isSticky, setIsSticky] = useState(false);
  const [originalTop, setOriginalTop] = useState<number>(0);

  useEffect(() => {
    function handleScroll() {
      const scrollTop = window.scrollY;
      // const header = document.querySelector("#menu_header") as HTMLElement;
      const headerHeight = 124;
      const top = originalTop;

      if (scrollTop + headerHeight >= top && !isSticky) {
        setIsSticky(true);
      } else if (scrollTop + headerHeight < top && isSticky) {
        setIsSticky(false);
      }
    }

    if (divRef.current) {
      const rect = divRef.current.getBoundingClientRect();
      setOriginalTop(rect.top + window.scrollY);
    }

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [isSticky, originalTop]);

  return (
    <div
      ref={divRef}
      className={`${
        isSticky
          ? "position-fixed shadow bg-doradoIMSS  w-100"
          : "bg-doradoIMSS"
      } transition-all`}
      style={{
        top: isSticky ? 124 : "auto",
        transition: "top 0.6s ease-in-out",
        zIndex: 1000,
      }}
    >
      <div className="container py-3">
        <h4>Catálogo de Unidades del CUUMS</h4>
      </div>
    </div>
  );
}

export default MenuFlotante;
