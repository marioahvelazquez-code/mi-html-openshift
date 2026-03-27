import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import logoBlanco from "../assets/img/logo-gob-mx.png";
import dpti from "../assets/img/dpti.png";

type Props = {
  onLoginSuccess: () => void;
};

type UsuarioFicha = {
  usuario: string;
  contrasena: string;
};

type UsuariosFichaResponse = {
  usuarios: UsuarioFicha[];
};

export default function PantallaLogin({ onLoginSuccess }: Props) {
  const [usuario, setUsuario] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState("");
  const [usuariosPermitidos, setUsuariosPermitidos] = useState<UsuarioFicha[]>([]);

  useEffect(() => {
    // #Mario: Inicio carga de usuarios locales para autenticacion temporal.
    const cargarUsuarios = async () => {
      try {
        const archivoUsuarios = new URL("../assets/usuarios_fichas.json", import.meta.url).href;
        const response = await fetch(archivoUsuarios);

        if (!response.ok) {
          throw new Error("No fue posible leer el archivo de usuarios.");
        }

        const data = (await response.json()) as UsuariosFichaResponse;
        setUsuariosPermitidos(data.usuarios ?? []);
      } catch {
        setError("No se pudo cargar el catalogo de usuarios.");
      }
    };

    cargarUsuarios();
    // #Mario: Fin carga de usuarios locales para autenticacion temporal.
  }, []);

  const manejarSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!usuario.trim() || !contrasena.trim()) {
      setError("Captura usuario y contrasena para continuar.");
      return;
    }

    const credencialesValidas = usuariosPermitidos.some(
      (item) => item.usuario === usuario.trim() && item.contrasena === contrasena.trim(),
    );

    if (!credencialesValidas) {
      setError("Usuario o contrasena incorrectos.");
      return;
    }

    setError("");
    onLoginSuccess();
  };

  return (
    <div className="login-screen">
      <div className="login-overlay" />

      <section className="login-card" aria-label="Autenticacion de acceso">
        <div className="login-brand">
          <img src={logoBlanco} className="login-logo-gob" alt="Gobierno de Mexico" />
          <div className="login-divider" />
          <img src={dpti} className="login-logo-dpti" alt="DPTI" />
        </div>

        <p className="login-kicker">Acceso al sistema</p>
        <h1 className="login-title">Autenticacion</h1>
        <p className="login-subtitle">Inicia sesion para acceder a Revisar Fichas</p>

        <form onSubmit={manejarSubmit} className="login-form">
          <label htmlFor="usuario" className="login-label">
            Usuario
          </label>
          <input
            id="usuario"
            type="text"
            className="login-input"
            value={usuario}
            onChange={(event) => setUsuario(event.target.value)}
            autoComplete="username"
          />

          <label htmlFor="contrasena" className="login-label">
            Contrasena
          </label>
          <input
            id="contrasena"
            type="password"
            className="login-input"
            value={contrasena}
            onChange={(event) => setContrasena(event.target.value)}
            autoComplete="current-password"
          />

          {error && <p className="login-error">{error}</p>}

          <button type="submit" className="login-button">
            Entrar
          </button>
        </form>
      </section>
    </div>
  );
}