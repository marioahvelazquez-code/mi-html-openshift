import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';

interface ModalSolicitud {
  abierto: boolean;
  titulo: string;
  mensaje: string;
  tipo: 'info' | 'warning' | 'success';
}

@Component({
  selector: 'app-solicitud-acceso-bd',
  imports: [CommonModule, FormsModule],
  templateUrl: './solicitud-acceso-bd.html',
  styleUrls: ['./solicitud-acceso-bd.css']
})
export class SolicitudAccesoBdComponent implements OnInit {
  nombre: string = '';
  rol: string = '';
  correo: string = '';
  coordinacion: string = '';
  matricula: string = '';
  basesSeleccionadas: string[] = [];

  enviando: boolean = false;
  modalSolicitud: ModalSolicitud = {
    abierto: false,
    titulo: '',
    mensaje: '',
    tipo: 'info',
  };

  constructor(
    private authService: AuthService,
    private http: HttpClient,
    private router: Router,
  ) {}

  ngOnInit() {
    const userDataStr = sessionStorage.getItem('userData');
    let userData: any = null;
    if (userDataStr) {
      try {
        userData = JSON.parse(userDataStr);
      } catch {
        userData = null;
      }
    }
    if (userData && userData.usuario) {
      const u = userData.usuario;
      this.nombre = `${u.nombre || ''} ${u.primerApellido || ''} ${u.segundoApellido || ''}`.trim();
      this.rol = u.descripcion || '';
      this.correo = u.nomCuenta || u.correo || '';
    }
  }

  cerrarModal(): void {
    this.modalSolicitud.abierto = false;
  }

  cerrarModalIrMenuPrincipal(): void {
    this.modalSolicitud.abierto = false;
    void this.router.navigate(['/home']);
  }

  private abrirModal(
    titulo: string,
    mensaje: string,
    tipo: 'info' | 'warning' | 'success' = 'info',
  ): void {
    this.modalSolicitud = { abierto: true, titulo, mensaje, tipo };
  }

  agregarBase(base: string) {
    if (!base) return;
    if (this.basesSeleccionadas.includes(base)) {
      this.quitarBase(base);
      return;
    }
    this.basesSeleccionadas = [...this.basesSeleccionadas, base];
  }

  quitarBase(base: string) {
    this.basesSeleccionadas = this.basesSeleccionadas.filter((b) => b !== base);
  }

  enviarSolicitud() {
    if (!this.nombre || !this.correo) {
      this.abrirModal(
        'Datos incompletos',
        'No se pudo obtener el nombre o correo del usuario autenticado.',
        'warning',
      );
      return;
    }
    if (this.basesSeleccionadas.length === 0) {
      this.abrirModal('Sin bases seleccionadas', 'Seleccione al menos una base de datos.', 'warning');
      return;
    }

    const token = sessionStorage.getItem('token') || '';
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });

    const payload = {
      nombre_completo: this.nombre,
      correo: this.correo,
      coordinacion: this.coordinacion,
      matricula: this.matricula,
      rol: this.rol,
      bases_datos_csv: this.basesSeleccionadas.join(','),
    };

    this.enviando = true;
    this.http.post<any>('/api/catalogos/solicitud-acceso-bd/', payload, { headers }).subscribe({
      next: (res) => {
        this.enviando = false;
        if (res.ok) {
          this.abrirModal(
            'Guardado exitoso',
            'Se registraron los datos de la solicitud correctamente.',
            'success',
          );
          this.coordinacion = '';
          this.matricula = '';
          this.basesSeleccionadas = [];
        } else {
          this.abrirModal('Error al enviar', res.mensaje || 'Error al enviar la solicitud.', 'warning');
        }
      },
      error: (err) => {
        this.enviando = false;
        this.abrirModal('Error de conexion', err?.error?.mensaje || 'Error al conectar con el servidor.', 'warning');
      },
    });
  }
}
