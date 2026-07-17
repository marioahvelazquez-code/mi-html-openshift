import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { of } from 'rxjs';
import { catchError, finalize, retry, timeout } from 'rxjs/operators';

interface MisSolicitudesResponse {
  ok: boolean;
  total?: number;
  items?: Record<string, unknown>[];
}

@Component({
  selector: 'app-solicitudes-especiales-realizadas',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './solicitudes-especiales-realizadas.html',
  styleUrl: './solicitudes-especiales-realizadas.css',
})
export class SolicitudesEspecialesRealizadasComponent implements OnInit {
  readonly columnasFijas = [
    { campo: 'ticket', etiqueta: 'Ticket' },
    { campo: 'nombre_completo', etiqueta: 'Nombre completo' },
    { campo: 'bases_datos_csv', etiqueta: 'Bases de datos' },
    { campo: 'tabla', etiqueta: 'Tabla' },
    { campo: 'cruce', etiqueta: 'Cruce' },
    { campo: 'con_quien_se_cruza', etiqueta: 'Con quien se cruza' },
    { campo: 'oficio_url', etiqueta: 'Oficio' },
    { campo: 'fecha_solicitud', etiqueta: 'Fecha de solicitud' },
    { campo: 'estatus', etiqueta: 'Estatus' },
  ];
  readonly totalSolicitudes = signal(0);
  readonly cargando = signal(true);
  readonly cargandoTabla = signal(false);
  readonly mostrarTabla = signal(false);
  readonly columnasTabla = signal<string[]>([]);

  readonly filasTabla = signal<Record<string, unknown>[]>([]);
  private readonly correoUsuario: string;
  private readonly nomCuentaUsuario: string;

  constructor(private http: HttpClient) {
    const userDataRaw = sessionStorage.getItem('userData');
    const sessionUsuario = (sessionStorage.getItem('usuario') || '').trim();

    let correo = '';
    let nomCuenta = '';

    if (userDataRaw) {
      try {
        const userData = JSON.parse(userDataRaw);
        const u = userData?.usuario || {};
        correo = String(u?.correo || '').trim();
        nomCuenta = String(u?.nomCuenta || '').trim();
      } catch {
        // Si falla el parse, usamos fallback por sesion.
      }
    }

    this.correoUsuario = correo || sessionUsuario;
    this.nomCuentaUsuario = nomCuenta || sessionUsuario;
  }

  ngOnInit(): void {
    this.cargarMisSolicitudes(false);
  }

  verMisSolicitudes(): void {
    if (this.mostrarTabla()) {
      this.mostrarTabla.set(false);
      return;
    }

    this.cargarMisSolicitudes(true);
  }

  private cargarMisSolicitudes(cargarTabla: boolean): void {
    if (!this.correoUsuario && !this.nomCuentaUsuario) {
      this.totalSolicitudes.set(0);
      this.filasTabla.set([]);
      this.columnasTabla.set([]);
      this.cargando.set(false);
      this.cargandoTabla.set(false);
      return;
    }

    this.cargando.set(!cargarTabla);
    this.cargandoTabla.set(cargarTabla);

    const query =
      `/api/catalogos/solicitud-especial-bd/?detalle=mis-solicitudes` +
      `&correo=${encodeURIComponent(this.correoUsuario)}` +
      `&nom_cuenta=${encodeURIComponent(this.nomCuentaUsuario)}`;

    this.http
      .get<MisSolicitudesResponse>(query)
      .pipe(
        timeout(15000),
        retry(1),
        catchError(() => of({ ok: false, total: 0, items: [] })),
        finalize(() => {
          this.cargando.set(false);
          this.cargandoTabla.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          const items = Array.isArray(res?.items) ? res.items : [];
          const total = Number(res?.total ?? items.length ?? 0);

          if (res?.ok && !Number.isNaN(total)) {
            this.totalSolicitudes.set(total);
          }

          if (cargarTabla) {
            this.columnasTabla.set(this.columnasFijas.map((c) => c.campo));
            this.filasTabla.set(items);
            this.mostrarTabla.set(true);
          }
        },
      });
  }
}
