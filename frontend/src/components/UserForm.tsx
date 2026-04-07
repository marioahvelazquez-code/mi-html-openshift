import { useState, useEffect } from "react";
import axios from "axios";

interface Usuario {
  clave: string;
  region: string;
  delegacion: string;
  nivel: string;
  unidad: string;
}

const UserForm = () => {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [nuevoUsuario, setNuevoUsuario] = useState<Usuario>({
    clave: "",
    region: "",
    delegacion: "",
    nivel: "",
    unidad: "",
  });

  // Consultar usuarios al cargar
  useEffect(() => {
    fetchUsuarios();
  }, []);

  const fetchUsuarios = () => {
    axios
      .get<Usuario[]>("http://localhost:8000/api/usuarios/")
      .then((res) => setUsuarios(res.data))
      .catch((error) => console.error("Error al obtener usuarios:", error));
  };
  // Enviar nuevo usuario
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    axios
      .post<Usuario>("http://localhost:8000/api/usuarios/", nuevoUsuario)
      .then((res) => {
        setUsuarios([...usuarios, res.data]);
        setNuevoUsuario({
          clave: "",
          region: "",
          delegacion: "",
          nivel: "",
          unidad: "",
        }); // Limpiar el formulario
      })
      .catch((error) => {
        console.error("Error al guardar el usuario:", error);
      });
  };

  const handleDelete = (clave: string) => {
    axios
      .delete(`http://localhost:8000/api/usuarios/${clave}/`)
      .then(() => fetchUsuarios())
      .catch((error) => {
        console.error("Error al eliminar el usuario:", error);
      });
  };

  return (
    <div>
      <h2>Usuarios</h2>
      <table
        border={1}
        cellPadding={8}
        style={{ borderCollapse: "collapse", width: "100%" }}
      >
        <thead>
          <tr>
            <th>Clave</th>
            <th>Región</th>
            <th>Delegación</th>
            <th>Nivel</th>
            <th>Unidad</th>
          </tr>
        </thead>
        <tbody>
          {usuarios.map((u) => (
            <tr key={u.clave}>
              <td>{u.clave}</td>
              <td>{u.region}</td>
              <td>{u.delegacion}</td>
              <td>{u.nivel}</td>
              <td>{u.unidad}</td>
              <td>
                <button onClick={() => handleDelete(u.clave)}>Eliminar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Agregar Unidad</h3>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="clave"
          value={nuevoUsuario.clave}
          onChange={(e) =>
            setNuevoUsuario({ ...nuevoUsuario, clave: e.target.value })
          }
        />
        <input
          type="text"
          placeholder="Región"
          value={nuevoUsuario.region}
          onChange={(e) =>
            setNuevoUsuario({ ...nuevoUsuario, region: e.target.value })
          }
        />
        <input
          type="text"
          placeholder="Delegación"
          value={nuevoUsuario.delegacion}
          onChange={(e) =>
            setNuevoUsuario({ ...nuevoUsuario, delegacion: e.target.value })
          }
        />
        <input
          type="text"
          placeholder="Nivel"
          value={nuevoUsuario.nivel}
          onChange={(e) =>
            setNuevoUsuario({ ...nuevoUsuario, nivel: e.target.value })
          }
        />
        <input
          type="text"
          placeholder="Unidad "
          value={nuevoUsuario.unidad}
          onChange={(e) =>
            setNuevoUsuario({ ...nuevoUsuario, unidad: e.target.value })
          }
        />
        <button type="submit">Guardar</button>
      </form>
    </div>
  );
};

export default UserForm;
