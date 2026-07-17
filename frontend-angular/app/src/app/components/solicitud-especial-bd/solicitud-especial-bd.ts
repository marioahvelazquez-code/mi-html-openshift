import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { finalize, timeout } from 'rxjs';
import { AuthService } from '../../services/auth';

interface ModalSolicitud {
  abierto: boolean;
  titulo: string;
  mensaje: string;
  tipo: 'info' | 'warning' | 'success';
}

@Component({
  selector: 'app-solicitud-especial-bd',
  imports: [CommonModule, FormsModule],
  templateUrl: './solicitud-especial-bd.html',
  styleUrls: ['./solicitud-especial-bd.css']
})
export class SolicitudEspecialBdComponent implements OnInit {
  nombre: string = '';
  rol: string = '';
  correo: string = '';
  coordinacion: string = '';
  tabla: string = '';
  cruce: 'SI' | 'NO' | '' = '';
  conQuienSeCruza: string = '';
  oficioNombreArchivo: string = '';
  oficioBase64: string = '';
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
    private cdr: ChangeDetectorRef,
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

  onCruceChange(): void {
    if (this.cruce !== 'SI') {
      this.conQuienSeCruza = '';
    }
  }

  onOficioSeleccionado(event: Event): void {
    const input = event.target as HTMLInputElement;
    const archivo = input.files?.[0];

    if (!archivo) {
      this.oficioNombreArchivo = '';
      this.oficioBase64 = '';
      return;
    }

    const esPdf = archivo.type === 'application/pdf' || archivo.name.toLowerCase().endsWith('.pdf');
    if (!esPdf) {
      this.abrirModal('Archivo no permitido', 'Solo se permiten archivos PDF para el oficio.', 'warning');
      input.value = '';
      this.oficioNombreArchivo = '';
      this.oficioBase64 = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const resultado = typeof reader.result === 'string' ? reader.result : '';
      const base64 = resultado.includes(',') ? resultado.split(',')[1] : '';
      this.oficioNombreArchivo = archivo.name;
      this.oficioBase64 = base64;
    };
    reader.onerror = () => {
      this.abrirModal('Error de lectura', 'No se pudo leer el archivo seleccionado.', 'warning');
      this.oficioNombreArchivo = '';
      this.oficioBase64 = '';
    };
    reader.readAsDataURL(archivo);
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
    if (this.cruce === 'SI' && !this.conQuienSeCruza.trim()) {
      this.abrirModal('Dato requerido', 'Indique con quien se cruza la informacion.', 'warning');
      return;
    }

    const token = sessionStorage.getItem('token') || '';
    const headers = new HttpHeaders({ Authorization: `Bearer ${token}` });

    const payload = {
      nombre_completo: this.nombre,
      correo: this.correo,
      coordinacion: this.coordinacion,
      rol: this.rol,
      tabla: this.tabla,
      cruce: this.cruce,
      con_quien_se_cruza: this.cruce === 'SI' ? this.conQuienSeCruza.trim() : '',
      oficio_nombre_archivo: this.oficioNombreArchivo,
      oficio_pdf_base64: this.oficioBase64,
      bases_datos_csv: this.basesSeleccionadas.join(','),
    };

    this.enviando = true;
    this.http
      .post<any>('/api/catalogos/solicitud-especial-bd/', payload, { headers })
      .pipe(
        timeout(15000),
        finalize(() => {
          this.enviando = false;
          this.cdr.detectChanges();
        }),
      )
      .subscribe({
      next: (res) => {
        if (res.ok) {
          const mensajeExito = res.ticket
            ? `Se registraron los datos de la solicitud correctamente. Ticket: ${res.ticket}`
            : 'Se registraron los datos de la solicitud correctamente.';
          this.abrirModal(
            'Guardado exitoso',
            mensajeExito,
            'success',
          );
          this.coordinacion = '';
          this.tabla = '';
          this.cruce = '';
          this.conQuienSeCruza = '';
          this.oficioNombreArchivo = '';
          this.oficioBase64 = '';
          this.basesSeleccionadas = [];
        } else {
          this.abrirModal('Error al enviar', res.mensaje || 'Error al enviar la solicitud.', 'warning');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        const mensaje =
          err?.name === 'TimeoutError'
            ? 'La solicitud esta tardando mas de lo esperado. Intente nuevamente en unos segundos.'
            : (err?.error?.mensaje || 'Error al conectar con el servidor.');
        this.abrirModal('Error de conexion', mensaje, 'warning');
        this.cdr.detectChanges();
      },
    });
  }
}
