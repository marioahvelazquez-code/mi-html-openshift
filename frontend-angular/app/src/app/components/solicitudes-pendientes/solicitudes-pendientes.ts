import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { of } from 'rxjs';
import { catchError, finalize, retry, timeout } from 'rxjs/operators';

interface ConteoSolicitudesResponse {
  ok: boolean;
  total?: number;
}

interface TablaSolicitudesResponse {
  ok: boolean;
  items?: Record<string, unknown>[];
}

interface AprobarSolicitudResponse {
  ok: boolean;
  mensaje?: string;
}

@Component({
  selector: 'app-solicitudes-pendientes',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './solicitudes-pendientes.html',
  styleUrl: './solicitudes-pendientes.css',
})
export class SolicitudesPendientesComponent implements OnInit {
  readonly totalPendientes = signal(0);
  readonly cargando = signal(true);
  readonly cargandoTabla = signal(false);
  readonly mostrarTabla = signal(false);
  readonly columnasTabla = signal<string[]>([]);
  readonly filasTabla = signal<Record<string, unknown>[]>([]);
  readonly modalAprobacionAbierto = signal(false);
  readonly aprobandoSolicitud = signal(false);
  readonly errorAprobacion = signal('');
  readonly usuarioAprobacion = signal('');
  readonly contrasenaAprobacion = signal('');
  readonly idSolicitudAprobacion = signal<string | number | null>(null);

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    const cache = sessionStorage.getItem('solicitudesPendientesCount');
    if (cache !== null) {
      const valorCache = Number(cache);
      if (!Number.isNaN(valorCache)) {
        this.totalPendientes.set(valorCache);
      }
    }

    this.cargarConteoPendientes();
  }

  private cargarConteoPendientes(): void {
    this.cargando.set(true);

    this.http
      .get<ConteoSolicitudesResponse>('/api/catalogos/solicitud-acceso-bd/?estatus=pendiente')
      .pipe(
        timeout(10000),
        retry(1),
        catchError(() => of({ ok: false, total: this.totalPendientes() })),
        finalize(() => {
          this.cargando.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          const totalRespuesta = Number(res?.total ?? this.totalPendientes());
          if (res?.ok && !Number.isNaN(totalRespuesta)) {
            this.totalPendientes.set(totalRespuesta);
          }
          sessionStorage.setItem('solicitudesPendientesCount', String(this.totalPendientes()));
        },
      });
  }

  aprobar(): void {
    if (this.mostrarTabla()) {
      this.mostrarTabla.set(false);
      return;
    }

    this.cargarTablaPendientes();
  }

  abrirModalAprobacion(fila: Record<string, unknown>): void {
    const idSolicitud = this.obtenerIdSolicitud(fila);
    if (idSolicitud === null) {
      this.errorAprobacion.set('No se pudo identificar la solicitud seleccionada.');
      return;
    }

    this.idSolicitudAprobacion.set(idSolicitud);
    this.usuarioAprobacion.set('');
    this.contrasenaAprobacion.set('');
    this.errorAprobacion.set('');
    this.modalAprobacionAbierto.set(true);
  }

  cerrarModalAprobacion(): void {
    this.modalAprobacionAbierto.set(false);
    this.aprobandoSolicitud.set(false);
    this.errorAprobacion.set('');
    this.usuarioAprobacion.set('');
    this.contrasenaAprobacion.set('');
    this.idSolicitudAprobacion.set(null);
  }

  confirmarAprobacion(): void {
    const idSolicitud = this.idSolicitudAprobacion();
    const usuario = this.usuarioAprobacion().trim();
    const contrasena = this.contrasenaAprobacion().trim();

    if (idSolicitud === null) {
      this.errorAprobacion.set('No se encontro el id de la solicitud a aprobar.');
      return;
    }

    if (!usuario || !contrasena) {
      this.errorAprobacion.set('Captura usuario y contrasena para aprobar la solicitud.');
      return;
    }

    this.aprobandoSolicitud.set(true);
    this.errorAprobacion.set('');

    this.http
      .post<AprobarSolicitudResponse>('/api/catalogos/solicitud-acceso-bd/', {
        accion: 'aprobar',
        id_solicitud: idSolicitud,
        usuario,
        contrasena,
      })
      .pipe(
        timeout(15000),
        finalize(() => {
          this.aprobandoSolicitud.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          if (!res?.ok) {
            this.errorAprobacion.set(res?.mensaje || 'No se pudo aprobar la solicitud.');
            return;
          }

          const filasActuales = this.filasTabla();
          const filasFiltradas = filasActuales.filter((fila) => this.obtenerIdSolicitud(fila) !== idSolicitud);
          this.filasTabla.set(filasFiltradas);

          const nuevoTotal = Math.max(0, this.totalPendientes() - 1);
          this.totalPendientes.set(nuevoTotal);
          sessionStorage.setItem('solicitudesPendientesCount', String(nuevoTotal));

          this.cerrarModalAprobacion();
        },
        error: (err) => {
          this.errorAprobacion.set(err?.error?.mensaje || 'Error al aprobar la solicitud.');
        },
      });
  }

  private obtenerIdSolicitud(fila: Record<string, unknown>): string | number | null {
    const candidatos = ['id_solicitud', 'ID_solicitud', 'idsolicitud', 'id'];

    for (const campo of candidatos) {
      if (Object.prototype.hasOwnProperty.call(fila, campo) && fila[campo] !== null && fila[campo] !== undefined) {
        return fila[campo] as string | number;
      }
    }

    return null;
  }

  private cargarTablaPendientes(): void {
    this.cargandoTabla.set(true);

    this.http
      .get<TablaSolicitudesResponse>('/api/catalogos/solicitud-acceso-bd/?estatus=pendiente&detalle=tabla')
      .pipe(
        timeout(15000),
        retry(1),
        catchError(() => of({ ok: false, items: [] })),
        finalize(() => {
          this.cargandoTabla.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          const items = Array.isArray(res?.items) ? res.items : [];
          const columnasOcultas = new Set(['id_solicitud', 'idsolicitud', 'id', 'nombre', 'nombre_completo', 'usuario', 'contrasena']);
          const columnas = items.length > 0
            ? Object.keys(items[0]).filter((columna) => !columnasOcultas.has(columna.toLowerCase()))
            : [];

          this.columnasTabla.set(columnas);
          this.filasTabla.set(items);
          this.mostrarTabla.set(true);
        },
      });
  }
}
