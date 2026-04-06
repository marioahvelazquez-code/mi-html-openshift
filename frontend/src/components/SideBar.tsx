import { useState } from 'react';

type Seccion = 'tableros' | 'informes' | 'descarga';

interface OpenState {
  tableros: boolean;
  informes: boolean;
  descarga: boolean;
}

const Sidebar: React.FC = () => {
  const [open, setOpen] = useState<OpenState>({
    tableros: false,
    informes: false,
    descarga: false,
  });

  const toggle = (seccion: Seccion): void => {
    setOpen((prev) => ({
      ...prev,
      [seccion]: !prev[seccion],
    }));
  };

  return (
    <div className="sticky-top menu_lateral col-12 col-md-4 col-lg-3 col-xl-2">
      <div id="accordion">
        {/* Inicio */}
        <div className="card">
          <div
            className="card-header btn btn-p7420 mb-0 p-2 text-white text-left active"
            role="tab"
            onClick={() => console.log('Redirigir a inicio')}
          >
            <div className="truncado">
              <a className="text-white d-block w-100" href="#!">
                <i className="icon icon-general"></i> | Inicio
              </a>
            </div>
          </div>
        </div>

        {/* Tableros de Información */}
        <div className="card">
          <div
            className="card-header btn btn-p7420 mb-0 p-2 text-white text-left"
            role="tab"
            onClick={() => toggle('tableros')}
          >
            <a className="text-white d-block w-100" href="#!">
              <i className="icon icon-recursos-salud"></i> | Tableros de Información
            </a>
          </div>
          {open.tableros && (
            <div className="list-group">
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Ficha Estatal</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Memoria Estadística</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Red Médica</small>
              </a>
            </div>
          )}
        </div>

        {/* Informes */}
        <div className="card">
          <div
            className="card-header btn btn-p7420 mb-0 p-2 text-white text-left"
            role="tab"
            onClick={() => toggle('informes')}
          >
            <a className="text-white d-block w-100" href="#!">
              <i className="icon icon-recursos-salud"></i> | Informes
            </a>
          </div>
          {open.informes && (
            <div className="list-group">
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Fichas Estatales</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Informes Analíticos</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Fichas Políticas</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Documentos de Apoyo</small>
              </a>
            </div>
          )}
        </div>

        {/* Descarga de Información */}
        <div className="card">
          <div
            className="card-header btn btn-p7420 mb-0 p-2 text-white text-left"
            role="tab"
            onClick={() => toggle('descarga')}
          >
            <a className="text-white d-block w-100" href="#!">
              <i className="icon icon-camas-hospitalarias"></i> | Descarga de Información
            </a>
          </div>
          {open.descarga && (
            <div className="list-group">
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Población IMSS</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Proyección Poblacional</small>
              </a>
              <a className="list-group-item pl-4 p-1 d-block" href="#!">
                <small className="font-weight-bold">Salario puestos de trabajo</small>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
