import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class IniciaSesion implements OnInit {
  private readonly usuarioStorageKey = 'usuarioAutenticado';
  usuario = '';
  contrasena = '';
  error = '';
  cargando = false;

  constructor(private readonly router: Router) {}

  ngOnInit(): void {}

  async iniciarSesion(): Promise<void> {
    this.error = '';

    const usuarioLimpio = this.usuario.trim();
    const contrasenaLimpia = this.contrasena.trim();

    if (!usuarioLimpio || !contrasenaLimpia) {
      this.error = 'Captura usuario y contrasena para continuar.';
      return;
    }

    const urlLogin = '/api/catalogos/autenticar/';

    try {
      this.cargando = true;

      const response = await fetch(urlLogin, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          usuario: usuarioLimpio,
          contrasena: contrasenaLimpia
        })
      });

      let data: { ok?: boolean; message?: string; requiere_cambio_pwd?: boolean } = {};
      try {
        data = (await response.json()) as {
          ok?: boolean;
          message?: string;
          requiere_cambio_pwd?: boolean;
        };
      } catch {
        data = {};
      }

      if (!response.ok || !data.ok) {
        this.error = data.message ?? 'Usuario o contrasena incorrectos.';
        return;
      }

      if (Boolean(data.requiere_cambio_pwd)) {
        void this.router.navigate(['/cambiar-password-primer-ingreso'], {
          state: {
            usuario: usuarioLimpio,
            contrasenaActual: contrasenaLimpia
          }
        });
        return;
      }

      localStorage.setItem(this.usuarioStorageKey, usuarioLimpio);
      void this.router.navigate(['/home']);
      return;
    } catch {
      this.error = 'No se pudo conectar con el servidor.';
    } finally {
      this.cargando = false;
    }
  }
}
