import { MoreVertical } from "lucide-react";

<nav className="navbar navbar-expand-lg navbar-dark sub-navbar bg-dorado">
  <div className="container">
    <button
      className="btn btn-outline-light "
      type="button"
      data-bs-toggle="offcanvas"
      data-bs-target="#menuLateral"
      aria-controls="menuLateral"
    >
      <MoreVertical size={24} />
    </button>

    <div
      className="collapse navbar-collapse justify-content-end"
      id="navbarSupportedContentTwo"
    >
      <ul className="navbar-nav">
        <li className="nav-item dropdown">
          <a
            className="nav-link text-white boton-negro font-weight-bold"
            href="#!"
            target="_top"
          >
            IMSS - Centro Estrat&eacute;gico de Datos en L&iacute;nea
          </a>
        </li>
        <li className="nav-item dropdown d-none d-lg-block d-xl-block">
          <a className="nav-link disabled text-white font-weight-bold"> | </a>
        </li>
        <li className="nav-item dropdown">
          <a
            className="nav-link text-white boton-negro font-weight-bold"
            href="#!"
          >
            {" "}
            CEDL
          </a>
        </li>
      </ul>
    </div>
  </div>
</nav>;
