import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-cambiar-password-primer-ingreso',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './cambiar-password-primer-ingreso.html',
  styleUrl: './cambiar-password-primer-ingreso.css'
})
export class CambiarPasswordPrimerIngreso {
  private readonly usuarioStorageKey = 'usuarioAutenticado';
  usuario = '';
  contrasenaActual = '';
  nuevaContrasena = '';
  confirmarContrasena = '';
  error = '';
  cargando = false;

  constructor(private readonly router: Router) {
    const state = history.state as { usuario?: string; contrasenaActual?: string };

    this.usuario = String(state?.usuario ?? '').trim();
    this.contrasenaActual = String(state?.contrasenaActual ?? '').trim();

    if (!this.usuario || !this.contrasenaActual) {
      void this.router.navigate(['/login']);
    }
  }

  async guardarYContinuar(): Promise<void> {
    this.error = '';

    const nueva = this.nuevaContrasena.trim();
    const confirmar = this.confirmarContrasena.trim();

    if (!nueva || !confirmar) {
      this.error = 'Captura y confirma la nueva contrasena para continuar.';
      return;
    }

    if (nueva !== confirmar) {
      this.error = 'La confirmacion de contrasena no coincide.';
      return;
    }

    const urlCambio = '/api/catalogos/cambiar-password-primer-ingreso/';

    try {
      this.cargando = true;

      const response = await fetch(urlCambio, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          usuario: this.usuario,
          contrasena_actual: this.contrasenaActual,
          nueva_contrasena: nueva
        })
      });

      let data: { ok?: boolean; message?: string } = {};
      try {
        data = (await response.json()) as { ok?: boolean; message?: string };
      } catch {
        data = {};
      }

      if (!response.ok || !data.ok) {
        this.error = data.message ?? 'No fue posible cambiar la contrasena.';
        return;
      }

      localStorage.setItem(this.usuarioStorageKey, this.usuario);
      void this.router.navigate(['/home']);
    } catch {
      this.error = 'No fue posible conectar con el servicio de cambio de contrasena.';
    } finally {
      this.cargando = false;
    }
  }

  volverAInicioSesion(): void {
    void this.router.navigate(['/login']);
  }
}
