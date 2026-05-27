  // ...existing code...



import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  NgZone,
  OnDestroy,
  OnInit,
  ViewChild,
  inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GlobalWorkerOptions, getDocument, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

type EstatusRevision = '' | 'correcta' | 'correccion';
interface RevisionPorPagina {
  estatus: EstatusRevision;
  comentario: string;
}

interface EntidadSqlItem {
  cve_edo?: string;
  nombre: string;
}

interface EntidadFichaItem {
  id: string;
  clave: string;
  nombre: string;
  nombre_pdf?: string;
  nombre_ppt?: string;
}

const ENTIDAD_POR_CLAVE: Record<string, string> = {
  AGU: 'Aguascalientes',
  BCN: 'Baja California',
  BCS: 'Baja California Sur',
  CAM: 'Campeche',
  COA: 'Coahuila',
  COL: 'Colima',
  CHP: 'Chiapas',
  CHH: 'Chihuahua',
  CMX: 'Ciudad de Mexico',
  DUR: 'Durango',
  GUA: 'Guanajuato',
  GRO: 'Guerrero',
  HID: 'Hidalgo',
  JAL: 'Jalisco',
  MEX: 'Estado de Mexico',
  MIC: 'Michoacan',
  MOR: 'Morelos',
  NAY: 'Nayarit',
  NLE: 'Nuevo Leon',
  OAX: 'Oaxaca',
  PUE: 'Puebla',
  QUE: 'Queretaro',
  ROO: 'Quintana Roo',
  SLP: 'San Luis Potosi',
  SIN: 'Sinaloa',
  SON: 'Sonora',
  TAB: 'Tabasco',
  TAM: 'Tamaulipas',
  TLA: 'Tlaxcala',
  VER: 'Veracruz',
  YUC: 'Yucatan',
  ZAC: 'Zacatecas',
};

const ORDEN_ENTIDAD_POR_CLAVE: Record<string, string> = {
  AGU: '01',
  BCN: '02',
  BCS: '03',
  CAM: '04',
  COA: '05',
  COL: '06',
  CHP: '07',
  CHH: '08',
  CMX: '09',
  DUR: '10',
  GUA: '11',
  GRO: '12',
  HID: '13',
  JAL: '14',
  MEX: '15',
  MIC: '16',
  MOR: '17',
  NAY: '18',
  NLE: '19',
  OAX: '20',
  PUE: '21',
  QUE: '22',
  ROO: '23',
  SLP: '24',
  SIN: '25',
  SON: '26',
  TAB: '27',
  TAM: '28',
  TLA: '29',
  VER: '30',
  YUC: '31',
  ZAC: '32',
};

const CLAVE_POR_ORDEN_ENTIDAD: Record<string, string> = Object.fromEntries(
  Object.entries(ORDEN_ENTIDAD_POR_CLAVE).map(([clave, orden]) => [orden, clave]),
);

const SUFIJO_FICHAS_ESTATALES = '25_05_2026';
const ARCHIVO_FICHA_NACIONAL_PDF = 'ficha_nacional.pdf';
const ARCHIVO_FICHA_NACIONAL_PPTX = 'FICHA_NACIONAL_14_05_2026.pptx';

interface FichaNacionalArchivos {
  pdf: string | null;
  pptx: string | null;
}

@Component({
  selector: 'app-revisar-ficha',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './revisar-ficha.html',
  styleUrl: './revisar-ficha.css',
})
export class RevisarFichaComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly cdr = inject(ChangeDetectorRef);
  entidadUsuario = '';

  get soloEntidadUsuario(): boolean {
    return !!this.entidadUsuario && this.entidadUsuario.toLowerCase() !== 'nacional';
  }

  // Mario: fichas locales servidas desde public/fichas.
  private readonly filesApiBase = '/public/fichas';
  private readonly nacionalFilesApiBase = '/public/nacional';

  @ViewChild('visorPdfRef') visorPdfRef?: ElementRef<HTMLElement>;
  @ViewChild('pdfCanvasRef') pdfCanvasRef?: ElementRef<HTMLCanvasElement>;


  constructor(private readonly ngZone: NgZone) {}


  descargarEstatalesZip(): void {
    const url = '/public/fichas/estatales.zip';
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = 'estatales.zip';
    document.body.appendChild(enlace);
    enlace.click();
    document.body.removeChild(enlace);
  }

  entidades: string[] = [];
  entidadesSql: EntidadSqlItem[] = [];
  entidadesConId: EntidadFichaItem[] = [];
  entidadSeleccionada = '';
  tipoFicha: 'estatal' | 'nacional' = 'estatal';
  hospitalSeleccionado = '';
  private hospitales: { id_Unidad: string; Nombre: string; NivelAtencion: string }[] = [];
  numPages = 0;
  paginaActual = 1;
  revisiones: RevisionPorPagina[] = [];
  revisionesBase: RevisionPorPagina[] = [];
  pdfWidth = 900;
  modalRevision = {
    abierto: false,
    titulo: '',
    mensaje: '',
    tipo: 'info' as 'info' | 'warning' | 'success',
  };

  private resizeObserver: ResizeObserver | null = null;
  private intervaloRecarga: number | null = null;
  private pdfDoc: PDFDocumentProxy | null = null;
  private renderTask: RenderTask | null = null;
  private fichaNacionalArchivos: FichaNacionalArchivos = {
    pdf: ARCHIVO_FICHA_NACIONAL_PDF,
    pptx: ARCHIVO_FICHA_NACIONAL_PPTX,
  };

  get hospitalesDisponibles(): { id_Unidad: string; Nombre: string; NivelAtencion: string }[] {
    return this.hospitales;
  }

  get pdfSeleccionado(): string | null {
    if (this.tipoFicha === 'nacional') {
      const archivo = this.fichaNacionalArchivos.pdf?.trim();
      return archivo ? this.construirUrlArchivoNacional(archivo) : null;
    }

    const archivoEntidad = this.entidadSeleccionadaMeta?.nombre_pdf?.trim();
    if (archivoEntidad) return this.construirUrlArchivo(archivoEntidad);

    return null;
  }

  get mostrandoPdf(): boolean {
    return Boolean(this.pdfSeleccionado && this.numPages > 0);
  }

  get pptSeleccionado(): string | null {
    if (this.tipoFicha === 'nacional') {
      const archivo = this.fichaNacionalArchivos.pptx?.trim();
      return archivo ? this.construirUrlArchivoNacional(archivo) : null;
    }

    const archivoEntidad = this.entidadSeleccionadaMeta?.nombre_ppt?.trim();
    if (archivoEntidad) return this.construirUrlArchivo(archivoEntidad);

    return null;
  }

  get revisionActual(): RevisionPorPagina {
    return this.revisiones[this.paginaActual - 1] || { estatus: '', comentario: '' };
  }

  get totalPaginasVisual(): number {
    return Math.max(this.numPages, this.revisiones.length, this.revisionesBase.length);
  }

  get paginaActualVisual(): number {
    if (!this.pdfSeleccionado || this.totalPaginasVisual === 0) return 0;
    return Math.max(1, Math.min(this.paginaActual, this.totalPaginasVisual));
  }

  get paginadorCargando(): boolean {
    return Boolean(this.pdfSeleccionado) && this.totalPaginasVisual === 0;
  }

  get paginaRevisada(): boolean {
    return this.revisionActual.estatus === 'correcta' || this.revisionActual.estatus === 'correccion';
  }

  get modalBadgeTexto(): string {
    if (this.modalRevision.tipo === 'success') return 'Completado';
    if (this.modalRevision.tipo === 'warning') return 'Atencion';
    return 'Informacion';
  }

  get usuarioAutenticado(): string {
    const usuarioLocal = localStorage.getItem('usuarioAutenticado')?.trim() ?? '';
    const usuarioSesion = sessionStorage.getItem('usuario')?.trim() ?? '';
    return usuarioLocal || usuarioSesion || 'sistema';
  }

  get ocultarRevision(): boolean {
    return (localStorage.getItem('statusUsuario') ?? '').trim() === '2';
  }

  private get authHeaders(): HeadersInit {
    return { 'Content-Type': 'application/json' };
  }

  ngOnInit(): void {
    // Mario: ruta de worker acorde a assets del proyecto actual.
    GlobalWorkerOptions.workerSrc = '/assets/pdf.worker.min.mjs';

    const entidad = localStorage.getItem('entidadUsuario');
    this.entidadUsuario = entidad ? entidad : '';

    void this.inicializarCatalogos();
    console.log('[RevisarFicha] ngOnInit llamado');
    console.log('[RevisarFicha] entidades antes:', this.entidades);
    window.addEventListener('resize', this.actualizarAnchoPdfBound);
    this.iniciarRecargaPeriodica();
  }

  private async inicializarCatalogos(): Promise<void> {
    await this.cargarFichaNacionalLocal();
    await this.cargarFichasLocales();
    await this.cargarEntidadesDesdeSql();

    if (this.tipoFicha === 'estatal') {
      await this.cargarPdfActual();
    }
  }

  private async cargarFichaNacionalLocal(): Promise<void> {
    try {
      const response = await fetch('/api/catalogos/ficha-nacional/', {
        cache: 'no-store',
        headers: this.authHeaders,
      });

      if (!response.ok) {
        return;
      }

      const data = (await response.json()) as {
        ok?: boolean;
        pdf?: string | null;
        pptx?: string | null;
      };

      if (!data?.ok) {
        return;
      }

      this.fichaNacionalArchivos = {
        pdf: data.pdf?.trim() || null,
        pptx: data.pptx?.trim() || null,
      };
    } catch {
      // Mario: fallback a nombres por defecto si el endpoint no responde.
    }
  }

  ngAfterViewInit(): void {
    this.resizeObserver = new ResizeObserver(() => this.actualizarAnchoPdf());
    const visor = this.visorPdfRef?.nativeElement;

    if (visor) {
      this.resizeObserver.observe(visor);
      this.actualizarAnchoPdf();
    }

    if (this.pdfDoc) {
      void this.renderizarPaginaActual();
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    window.removeEventListener('resize', this.actualizarAnchoPdfBound);

    if (this.intervaloRecarga !== null) {
      window.clearInterval(this.intervaloRecarga);
    }

    void this.renderTask?.cancel();
    void this.pdfDoc?.destroy();
  }

  seleccionarEntidad(entidad: string): void {
    this.entidadSeleccionada = entidad;
    this.hospitalSeleccionado = '';
    this.limpiarRevision();

    void this.cargarPdfActual();
  }

  seleccionarTipoFicha(tipo: 'estatal' | 'nacional'): void {
    this.tipoFicha = tipo;

    if (tipo === 'estatal') {
      this.hospitalSeleccionado = '';
      this.hospitales = [];
    }

    this.limpiarRevision();

    if (tipo === 'estatal') {
      void this.cargarPdfActual();
    } else {
      void this.cargarPdfActual();
    }
  }

  seleccionarHospital(idUnidad: string): void {
    this.hospitalSeleccionado = idUnidad;
    this.limpiarRevision();
    void this.cargarPdfActual();
  }

  onDocumentLoadError(): void {
    this.numPages = 0;
    this.abrirModal('Error al cargar la ficha', 'No se pudo cargar el PDF seleccionado.', 'warning');
  }

  siguiente(): void {
    if (this.paginaActual < this.numPages) {
      this.paginaActual += 1;
      void this.renderizarPaginaActual();
    }
  }

  anterior(): void {
    if (this.paginaActual > 1) {
      this.paginaActual -= 1;
      void this.renderizarPaginaActual();
    }
  }

  cambiarEstatus(estatus: EstatusRevision): void {
    const idx = this.paginaActual - 1;
    if (!this.revisiones[idx]) return;

    this.revisiones[idx] = {
      ...this.revisiones[idx],
      estatus,
      comentario: estatus === 'correcta' ? '' : this.revisiones[idx].comentario,
    };
  }

  cambiarComentario(texto: string): void {
    const idx = this.paginaActual - 1;
    if (!this.revisiones[idx]) return;

    this.revisiones[idx] = { ...this.revisiones[idx], comentario: texto };
  }

  cerrarModal(): void {
    this.modalRevision.abierto = false;
  }

  async guardarRevision(): Promise<void> {
    if (!this.pdfSeleccionado) {
      this.abrirModal('Sin ficha cargada', 'No hay una ficha cargada para guardar revision.', 'warning');
      return;
    }

    console.log('[RevisarFicha] guardarRevision click', {
      paginaActual: this.paginaActual,
      totalRevisiones: this.revisiones.length,
      baseObjeto: this.obtenerBaseObjeto(),
    });

    const revisadas = this.revisiones
      .map((r, i) => ({ pagina: i + 1, r, base: this.revisionesBase[i] || { estatus: '', comentario: '' } }))
      .filter(({ r }) => r.estatus === 'correcta' || r.estatus === 'correccion');

    if (revisadas.length === 0) {
      this.abrirModal('Sin revision', 'Marca al menos una pagina como Aprobado o Requiere correccion.', 'info');
      return;
    }

    let guardables = revisadas.filter(
      ({ r, base }) =>
        r.estatus !== base.estatus || (r.comentario || '') !== (base.comentario || ''),
    );

    if (guardables.length === 0) {
      guardables = revisadas;
    }

    console.log('[RevisarFicha] paginas a guardar', guardables.map((g) => g.pagina));

    try {
      for (const { pagina, r } of guardables) {
        const random6 = () => Math.floor(100000 + Math.random() * 900000).toString();
        const id = random6();
        const id_bitacora = random6();

        const payload = {
          id,
          id_bitacora,
          id_user: this.usuarioAutenticado,
          id_presentacion: this.tipoFicha,
          id_objeto: `${this.obtenerBaseObjeto()}_${pagina}`,
          comentario: r.comentario || '',
          estatus: r.estatus === 'correcta' ? 'Aprobado' : 'Requiere correccion',
        };

        console.log('[RevisarFicha] POST /bitacora payload', payload);

        const res = await fetch('/api/catalogos/bitacora/', {
          method: 'POST',
          headers: this.authHeaders,
          body: JSON.stringify(payload),
        });

        const respuestaTexto = await res.text();
        console.log('[RevisarFicha] POST /bitacora response', {
          status: res.status,
          ok: res.ok,
          body: respuestaTexto,
        });

        if (!res.ok) {
          this.abrirModal(
            'Error al guardar',
            `No se pudo guardar la pagina ${pagina}. ${respuestaTexto || ''}`.trim(),
            'warning',
          );
          return;
        }
      }

      this.revisionesBase = this.clonarRevisiones(this.revisiones);
      this.abrirModal(
        'Guardado exitoso',
        `Se guardaron ${guardables.length} paginas correctamente.`,
        'success',
      );
    } catch {
      this.abrirModal('Error de conexion', 'Error de conexion al guardar.', 'warning');
    }
  }

  async finalizarRevision(): Promise<void> {
    if (!this.pdfSeleccionado || this.numPages <= 0) {
      this.abrirModal('Sin ficha cargada', 'No hay una ficha cargada.', 'warning');
      return;
    }

    const faltantes = Array.from({ length: this.numPages }, (_, i) => i + 1).filter((p) => {
      const r = this.revisiones[p - 1];
      return !(r?.estatus === 'correcta' || r?.estatus === 'correccion');
    });

    if (faltantes.length > 0) {
      this.abrirModal('Paginas pendientes', `Faltan por revisar: ${faltantes.join(', ')}`, 'warning');
      return;
    }

    try {
      const res = await fetch('/api/catalogos/bitacora/reporte-excel/', {
        method: 'POST',
        headers: this.authHeaders,
        body: JSON.stringify({
          id_user: this.usuarioAutenticado,
          id_presentacion: this.tipoFicha,
          id_objeto_base: this.obtenerBaseObjeto(),
          revisiones: this.revisiones,
        }),
      });

      if (!res.ok) {
        this.abrirModal('Error', 'No se pudo generar el reporte.', 'warning');
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `reporte_revision_${this.obtenerBaseObjeto()}.xls`;
      enlace.click();
      URL.revokeObjectURL(url);
      this.abrirModal('Revision finalizada', 'Se genero el reporte en Excel.', 'success');
    } catch {
      this.abrirModal('Error de conexion', 'Error al generar el reporte.', 'warning');
    }
  }

  descargarPpt(): void {
    void this.descargarPptConToken();
  }

  private abrirModal(
    titulo: string,
    mensaje: string,
    tipo: 'info' | 'warning' | 'success' = 'info',
  ): void {
    this.actualizarVista(() => {
      this.modalRevision = { abierto: true, titulo, mensaje, tipo };
    });
  }

  private actualizarVista(callback: () => void): void {
    this.ngZone.run(() => {
      callback();
      this.cdr.detectChanges();
    });
  }

  // Mario: carga de fichas disponibles desde carpeta local (manifest).
  private async cargarFichasLocales(): Promise<void> {
    this.entidadesConId = Object.entries(ENTIDAD_POR_CLAVE)
      .map(([clave, nombre]) => {
        const orden = ORDEN_ENTIDAD_POR_CLAVE[clave];
        return {
          id: orden,
          clave,
          nombre,
          nombre_pdf: this.construirNombreFichaEstatal(orden, clave, '.pdf'),
          nombre_ppt: this.construirNombreFichaEstatal(orden, clave, '.pptx'),
        };
      })
      .filter((item) => Boolean(item.id))
      .sort((a, b) => a.id.localeCompare(b.id));

    console.log('[RevisarFicha] entidadesConId cargadas:', this.entidadesConId.length);
  }

  // Mario: entidades se consumen del backend SQL (cat_entidad) via /api/catalogos/entidades/.
  private async cargarEntidadesDesdeSql(): Promise<void> {
    try {
      const res = await fetch('/api/catalogos/entidades/', { cache: 'no-store' });
      console.log('[RevisarFicha] Endpoint response status:', res.status);
      if (!res.ok) {
        this.ngZone.run(() => {
          this.entidades = [];
          this.entidadSeleccionada = '';
          this.cdr.detectChanges();
        });
        return;
      }

      const payload = (await res.json()) as EntidadSqlItem[];
      console.log('[RevisarFicha] Payload SQL recibido:', payload.length, payload.slice(0, 3));
      const entidadesSql = Array.isArray(payload)
        ? payload.filter((item) => String(item?.nombre ?? '').trim().length > 0)
        : [];

      const disponiblesPorClave = new Set(this.entidadesConId.map((item) => item.clave));
      const disponiblesPorNombre = new Map(
        this.entidadesConId.map((item) => [this.normalizarTexto(item.nombre), item]),
      );

      let entidadesDisponibles = entidadesSql.filter((item) => {
        const clave = String(item?.cve_edo ?? '')
          .trim()
          .toUpperCase();

        if (clave) {
          return disponiblesPorClave.has(clave);
        }

        return disponiblesPorNombre.has(this.normalizarTexto(item.nombre));
      });

      if (entidadesDisponibles.length === 0) {
        entidadesDisponibles = entidadesSql.length > 0
          ? [...entidadesSql]
          : this.entidadesConId.map((item) => ({ cve_edo: item.clave, nombre: item.nombre }));
      }

      if (this.soloEntidadUsuario) {
        const entidadNormalizada = this.normalizarTexto(this.entidadUsuario);
        entidadesDisponibles = entidadesDisponibles.filter(
          (item) => this.normalizarTexto(item.nombre) === entidadNormalizada,
        );
      }

      this.ngZone.run(() => {
        this.entidadesSql = entidadesDisponibles;
        this.entidades = entidadesDisponibles.map((item) => item.nombre);
        console.log(
          '[RevisarFicha] Entidades disponibles para combo:',
          this.entidades.length,
          this.entidades.slice(0, 3),
        );
        this.entidadSeleccionada = this.entidades[0] ?? '';
        this.cdr.detectChanges();
      });
    } catch {
      this.ngZone.run(() => {
        this.entidadesSql = [];
        this.entidades = [];
        this.entidadSeleccionada = '';
        this.cdr.detectChanges();
      });
      console.error('[RevisarFicha] Error cargando entidades SQL');
    }
  }

  private normalizarTexto(valor: string): string {
    return valor
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  private get entidadIdSeleccionada(): string {
    return this.entidadSeleccionadaMeta?.id ?? '';
  }

  private get entidadSqlSeleccionada(): EntidadSqlItem | null {
    const seleccion = this.normalizarTexto(this.entidadSeleccionada);
    return this.entidadesSql.find((item) => this.normalizarTexto(item.nombre) === seleccion) ?? null;
  }

  private get entidadSeleccionadaMeta(): EntidadFichaItem | null {
    const cveEdo = String(this.entidadSqlSeleccionada?.cve_edo ?? '')
      .trim()
      .toUpperCase();

    const clave = CLAVE_POR_ORDEN_ENTIDAD[cveEdo] ?? cveEdo;

    if (clave) {
      return this.entidadesConId.find((item) => item.clave === clave) ?? null;
    }

    const seleccion = this.normalizarTexto(this.entidadSeleccionada);
    return this.entidadesConId.find((item) => this.normalizarTexto(item.nombre) === seleccion) ?? null;
  }

  private construirNombreFichaEstatal(
    orden: string,
    clave: string,
    extension: '.pdf' | '.pptx',
  ): string {
    return `FE_${orden}_${clave}_${SUFIJO_FICHAS_ESTATALES}${extension}`;
  }

  private async cargarHospitales(): Promise<void> {
    // Mario: esta pantalla usa solo fichas locales estatales.
    this.hospitales = [];
  }

  private async cargarRevisionesGuardadas(totalPaginas: number): Promise<void> {
    const vacias: RevisionPorPagina[] = Array.from({ length: totalPaginas }, () => ({
      estatus: '',
      comentario: '',
    }));

    if (!this.pdfSeleccionado || totalPaginas <= 0) {
      this.actualizarVista(() => {
        this.revisiones = this.clonarRevisiones(vacias);
        this.revisionesBase = this.clonarRevisiones(vacias);
      });
      return;
    }

    try {
      const res = await fetch(
        `/api/catalogos/bitacora/?id_user=${encodeURIComponent(this.usuarioAutenticado)}&id_presentacion=${encodeURIComponent(this.tipoFicha)}&id_objeto_base=${encodeURIComponent(this.obtenerBaseObjeto())}`,
        { cache: 'no-store', headers: this.authHeaders },
      );

      if (!res.ok) {
        this.actualizarVista(() => {
          this.revisiones = this.clonarRevisiones(vacias);
          this.revisionesBase = this.clonarRevisiones(vacias);
        });
        return;
      }

      const data: unknown = await res.json();
      const items =
        data && typeof data === 'object' && Array.isArray((data as { items?: unknown[] }).items)
          ? (data as { items: Array<{ pagina?: number; estatus?: string; comentario?: string }> }).items
          : [];

      for (const item of items) {
        const pagina = Number(item.pagina);
        if (!Number.isInteger(pagina) || pagina < 1 || pagina > totalPaginas) continue;

        const estatusRaw = String(item.estatus || '').trim().toLowerCase();
        vacias[pagina - 1] = {
          estatus:
            estatusRaw === 'aprobado'
              ? 'correcta'
              : estatusRaw.includes('correcci')
                ? 'correccion'
                : '',
          comentario: String(item.comentario || ''),
        };
      }

      this.actualizarVista(() => {
        this.revisiones = this.clonarRevisiones(vacias);
        this.revisionesBase = this.clonarRevisiones(vacias);
      });
    } catch {
      this.actualizarVista(() => {
        this.revisiones = this.clonarRevisiones(vacias);
        this.revisionesBase = this.clonarRevisiones(vacias);
      });
    }
  }

  private obtenerBaseObjeto(): string {
    const nombrePdf =
      this.tipoFicha === 'nacional'
        ? (this.fichaNacionalArchivos.pdf?.trim() || ARCHIVO_FICHA_NACIONAL_PDF)
        : (this.entidadSeleccionadaMeta?.nombre_pdf?.trim() ||
          `Ficha_Estatal_${this.entidadSeleccionada}.pdf`);

    return nombrePdf.replace(/\.pdf$/i, '').replace(/\s+/g, '_');
  }

  private obtenerArchivoHospital(extension: '.pdf' | '.pptx'): string | null {
    const idUnidad = this.hospitalSeleccionado.trim();
    if (!idUnidad) return null;
    return `${idUnidad}${extension}`;
  }

  private construirUrlArchivo(nombreArchivo: string): string {
    return `${this.filesApiBase}/${encodeURIComponent(nombreArchivo)}`;
  }

  private construirUrlArchivoNacional(nombreArchivo: string): string {
    return `${this.nacionalFilesApiBase}/${encodeURIComponent(nombreArchivo)}`;
  }

  private limpiarRevision(): void {
    this.actualizarVista(() => {
      this.paginaActual = 1;
      this.numPages = 0;
      this.revisiones = [];
      this.revisionesBase = [];
    });
  }

  private hayCambiosLocales(): boolean {
    return this.revisiones.some((r, i) => {
      const b = this.revisionesBase[i] || { estatus: '', comentario: '' };
      return r.estatus !== b.estatus || (r.comentario || '') !== (b.comentario || '');
    });
  }

  private iniciarRecargaPeriodica(): void {
    if (this.intervaloRecarga !== null) window.clearInterval(this.intervaloRecarga);

    this.intervaloRecarga = window.setInterval(() => {
      if (!this.pdfSeleccionado || this.numPages <= 0 || this.hayCambiosLocales()) {
        return;
      }
      void this.cargarRevisionesGuardadas(this.numPages);
    }, 3000);
  }

  private clonarRevisiones(items: RevisionPorPagina[]): RevisionPorPagina[] {
    return items.map((item) => ({ estatus: item.estatus, comentario: item.comentario }));
  }

  private readonly actualizarAnchoPdfBound = (): void => {
    this.actualizarAnchoPdf();
  };

  private actualizarAnchoPdf(): void {
    const c = this.visorPdfRef?.nativeElement ?? null;
    if (!c) return;

    this.pdfWidth = Math.max(220, Math.min(504, c.clientWidth - 16));
    void this.renderizarPaginaActual();
  }

  private async cargarPdfActual(): Promise<void> {
    const rutaPdf = this.pdfSeleccionado;

    if (!rutaPdf) {
      await this.liberarDocumentoPdf();
      return;
    }

    try {
      await this.liberarDocumentoPdf();
      const response = await fetch(rutaPdf, { headers: this.authHeaders });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const pdfBlob = await response.blob();
      const arrayBuffer = await pdfBlob.arrayBuffer();
      const loadingTask = getDocument({
        data: new Uint8Array(arrayBuffer),
        disableWorker: true,
      } as any);

      this.pdfDoc = await loadingTask.promise;

      this.actualizarVista(() => {
        this.numPages = this.pdfDoc?.numPages ?? 0;
        this.paginaActual = 1;
      });

      await this.cargarRevisionesGuardadas(this.numPages);
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      await this.renderizarPaginaActual();
    } catch {
      await this.liberarDocumentoPdf();
      this.ngZone.run(() => this.onDocumentLoadError());
    }
  }

  private async renderizarPaginaActual(): Promise<void> {
    if (
      !this.pdfDoc ||
      !this.pdfCanvasRef?.nativeElement ||
      this.paginaActual < 1 ||
      this.paginaActual > this.numPages
    ) {
      return;
    }

    try {
      const pagina = await this.pdfDoc.getPage(this.paginaActual);
      const viewportBase = pagina.getViewport({ scale: 1 });
      const anchoDisponible = Math.max(220, this.pdfWidth);
      const escala = anchoDisponible / viewportBase.width;
      const viewport = pagina.getViewport({ scale: Math.max(0.25, escala) });
      const canvas = this.pdfCanvasRef.nativeElement;
      const context = canvas.getContext('2d');

      if (!context) {
        return;
      }

      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;

      if (this.renderTask) {
        await this.renderTask.cancel();
        this.renderTask = null;
      }

      context.clearRect(0, 0, canvas.width, canvas.height);

      this.renderTask = pagina.render({ canvasContext: context, viewport, canvas });
      await this.renderTask.promise;
      this.renderTask = null;
    } catch (error) {
      if (!(error instanceof Error) || error.name !== 'RenderingCancelledException') {
        this.onDocumentLoadError();
      }
    }
  }

  private async liberarDocumentoPdf(): Promise<void> {
    if (this.renderTask) {
      await this.renderTask.cancel();
      this.renderTask = null;
    }

    if (this.pdfDoc) {
      await this.pdfDoc.destroy();
      this.pdfDoc = null;
    }

    const canvas = this.pdfCanvasRef?.nativeElement;
    const context = canvas?.getContext('2d');

    if (canvas && context) {
      context.clearRect(0, 0, canvas.width, canvas.height);
      canvas.width = 0;
      canvas.height = 0;
    }
  }

  private async descargarPptConToken(): Promise<void> {
    if (!this.pptSeleccionado) return;

    try {
      const response = await fetch(this.pptSeleccionado, { headers: this.authHeaders });

      if (!response.ok) {
        this.abrirModal('Error al descargar', 'No se pudo descargar la ficha PPT.', 'warning');
        return;
      }

      const extension = this.pptSeleccionado.toLowerCase().includes('.pptx') ? '.pptx' : '.ppt';
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download =
        this.tipoFicha === 'nacional'
          ? `Ficha_Nacional${extension}`
          : `Ficha_Estatal_${this.entidadSeleccionada}${extension}`;
      enlace.click();
      URL.revokeObjectURL(url);
    } catch {
      this.abrirModal('Error de conexion', 'Error al descargar la ficha PPT.', 'warning');
    }
  }
}
