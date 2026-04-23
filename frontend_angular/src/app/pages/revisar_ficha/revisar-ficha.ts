import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, NgZone, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { GlobalWorkerOptions, getDocument, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

type EstatusRevision = '' | 'correcta' | 'correccion';
interface RevisionPorPagina { estatus: EstatusRevision; comentario: string; }

@Component({
  selector: 'app-revisar-ficha',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './revisar-ficha.html',
  styleUrl: './revisar-ficha.css'
})
export class RevisarFichaComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly usuarioStorageKey = 'usuarioAutenticado';
  @ViewChild('visorPdfRef') visorPdfRef?: ElementRef<HTMLElement>;
  @ViewChild('pdfCanvasRef') pdfCanvasRef?: ElementRef<HTMLCanvasElement>;

  constructor(private readonly ngZone: NgZone) {}

  readonly ENTIDADES: string[] = [
    'Aguascalientes','Baja California','Baja California Sur','Campeche','Coahuila','Colima',
    'Chiapas','Chihuahua','Ciudad de México','Durango','Guanajuato','Guerrero','Hidalgo',
    'Jalisco','Estado de México','Michoacán','Morelos','Nayarit','Nuevo León','Oaxaca',
    'Puebla','Querétaro','Quintana Roo','San Luis Potosí','Sinaloa','Sonora','Tabasco',
    'Tamaulipas','Tlaxcala','Veracruz','Yucatán','Zacatecas'
  ];

  readonly pdfFiles: string[] = [
    'Ficha_Estatal_AGUASCALIENTES.pdf','Ficha_Estatal_BAJA CALIFORNIA.pdf','Ficha_Estatal_BAJA CALIFORNIA SUR.pdf',
    'Ficha_Estatal_CAMPECHE.pdf','Ficha_Estatal_COAHUILA.pdf','Ficha_Estatal_COLIMA.pdf',
    'Ficha_Estatal_CHIAPAS.pdf','Ficha_Estatal_CHIHUAHUA.pdf','Ficha_Estatal_CIUDAD DE MÉXICO.pdf',
    'Ficha_Estatal_DURANGO.pdf','Ficha_Estatal_ESTADO DE MÉXICO.pdf','Ficha_Estatal_GUANAJUATO.pdf',
    'Ficha_Estatal_GUERRERO.pdf','Ficha_Estatal_HIDALGO.pdf','Ficha_Estatal_JALISCO.pdf',
    'Ficha_Estatal_MICHOACÁN.pdf','Ficha_Estatal_MORELOS.pdf','Ficha_Estatal_NAYARIT.pdf',
    'Ficha_Estatal_NUEVO LEÓN.pdf','Ficha_Estatal_OAXACA.pdf','Ficha_Estatal_PUEBLA.pdf',
    'Ficha_Estatal_QUERÉTARO.pdf','Ficha_Estatal_QUINTANA ROO.pdf','Ficha_Estatal_SAN LUIS POTOSÍ.pdf',
    'Ficha_Estatal_SINALOA.pdf','Ficha_Estatal_SONORA.pdf','Ficha_Estatal_TABASCO.pdf',
    'Ficha_Estatal_TAMAULIPAS.pdf','Ficha_Estatal_TLAXCALA.pdf','Ficha_Estatal_VERACRUZ.pdf',
    'Ficha_Estatal_YUCATÁN.pdf','Ficha_Estatal_ZACATECAS.pdf'
  ];

  readonly pptFiles: string[] = [
    'Ficha_Estatal_AGUASCALIENTES.pptx','Ficha_Estatal_BAJA CALIFORNIA.pptx','Ficha_Estatal_BAJA CALIFORNIA SUR.pptx',
    'Ficha_Estatal_CAMPECHE.pptx','Ficha_Estatal_COAHUILA.pptx','Ficha_Estatal_COLIMA.pptx',
    'Ficha_Estatal_CHIAPAS.pptx','Ficha_Estatal_CHIHUAHUA.pptx','Ficha_Estatal_CIUDAD DE MÉXICO.pptx',
    'Ficha_Estatal_DURANGO.pptx','Ficha_Estatal_ESTADO DE MÉXICO.pptx','Ficha_Estatal_GUANAJUATO.pptx',
    'Ficha_Estatal_GUERRERO.pptx','Ficha_Estatal_HIDALGO.pptx','Ficha_Estatal_JALISCO.pptx',
    'Ficha_Estatal_MICHOACÁN.pptx','Ficha_Estatal_MORELOS.pptx','Ficha_Estatal_NAYARIT.pptx',
    'Ficha_Estatal_NUEVO LEÓN.pptx','Ficha_Estatal_OAXACA.pptx','Ficha_Estatal_PUEBLA.pptx',
    'Ficha_Estatal_QUERÉTARO.pptx','Ficha_Estatal_QUINTANA ROO.pptx','Ficha_Estatal_SAN LUIS POTOSÍ.pptx',
    'Ficha_Estatal_SINALOA.pptx','Ficha_Estatal_SONORA.pptx','Ficha_Estatal_TABASCO.pptx',
    'Ficha_Estatal_TAMAULIPAS.pptx','Ficha_Estatal_TLAXCALA.pptx','Ficha_Estatal_VERACRUZ.pptx',
    'Ficha_Estatal_YUCATÁN.pptx','Ficha_Estatal_ZACATECAS.pptx'
  ];

  entidades = [...this.ENTIDADES];
  entidadSeleccionada = 'Aguascalientes';
  tipoFicha: 'estatal' | 'hospitalaria' = 'estatal';
  hospitalSeleccionado = '';
  numPages = 0;
  paginaActual = 1;
  revisiones: RevisionPorPagina[] = [];
  revisionesBase: RevisionPorPagina[] = [];
  pdfWidth = 900;
  modalRevision = { abierto: false, titulo: '', mensaje: '', tipo: 'info' as 'info' | 'warning' | 'success' };

  private resizeObserver: ResizeObserver | null = null;
  private intervaloRecarga: number | null = null;
  private pdfDoc: PDFDocumentProxy | null = null;
  private renderTask: RenderTask | null = null;

  get hospitalesDisponibles(): string[] { return []; }

  get pdfSeleccionado(): string | null {
    if (this.tipoFicha !== 'estatal') return null;
    const archivo = this.obtenerPdfPorEntidad(this.entidadSeleccionada);
    return archivo ? `/Fichas_estatales/${archivo}` : null;
  }

  get mostrandoPdf(): boolean { return Boolean(this.pdfSeleccionado && this.numPages > 0); }

  get pptSeleccionado(): string | null {
    if (this.tipoFicha !== 'estatal') return null;
    const archivo = this.obtenerPptPorEntidad(this.entidadSeleccionada);
    return archivo ? `/Fichas_estatales/${archivo}` : null;
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

  get paginadorCargando(): boolean { return Boolean(this.pdfSeleccionado) && this.totalPaginasVisual === 0; }
  get paginaRevisada(): boolean { return this.revisionActual.estatus === 'correcta' || this.revisionActual.estatus === 'correccion'; }

  get modalBadgeTexto(): string {
    if (this.modalRevision.tipo === 'success') return 'Completado';
    if (this.modalRevision.tipo === 'warning') return 'Atencion';
    return 'Informacion';
  }

  get usuarioAutenticado(): string {
    return localStorage.getItem(this.usuarioStorageKey)?.trim() ?? '';
  }

  ngOnInit(): void {
    GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
    void this.cargarEntidades();
    window.addEventListener('resize', this.actualizarAnchoPdfBound);
    this.iniciarRecargaPeriodica();
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
    if (this.intervaloRecarga !== null) { window.clearInterval(this.intervaloRecarga); }
    void this.renderTask?.cancel();
    void this.pdfDoc?.destroy();
  }

  seleccionarEntidad(entidad: string): void {
    this.entidadSeleccionada = entidad;
    this.hospitalSeleccionado = '';
    this.limpiarRevision();
    void this.cargarPdfActual();
  }

  seleccionarTipoFicha(tipo: 'estatal' | 'hospitalaria'): void {
    this.tipoFicha = tipo;
    if (tipo === 'estatal') this.hospitalSeleccionado = '';
    this.limpiarRevision();
    if (tipo === 'estatal') {
      void this.cargarPdfActual();
    } else {
      void this.liberarDocumentoPdf();
    }
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
    this.revisiones[idx] = { ...this.revisiones[idx], estatus, comentario: estatus === 'correcta' ? '' : this.revisiones[idx].comentario };
  }

  cambiarComentario(texto: string): void {
    const idx = this.paginaActual - 1;
    if (!this.revisiones[idx]) return;
    this.revisiones[idx] = { ...this.revisiones[idx], comentario: texto };
  }

  cerrarModal(): void { this.modalRevision.abierto = false; }

  async guardarRevision(): Promise<void> {
    if (!this.pdfSeleccionado) return;
    if (!this.usuarioAutenticado) { this.abrirModal('Sesion requerida', 'Inicia sesion nuevamente para guardar la revision.', 'warning'); return; }
    const guardables = this.revisiones
      .map((r, i) => ({ pagina: i + 1, r, base: this.revisionesBase[i] || { estatus: '', comentario: '' } }))
      .filter(({ r, base }) => (r.estatus === 'correcta' || r.estatus === 'correccion') && (r.estatus !== base.estatus || (r.comentario || '') !== (base.comentario || '')));

    if (guardables.length === 0) { this.abrirModal('Sin cambios', 'No hay cambios nuevos por guardar.', 'info'); return; }

    try {
      for (const { pagina, r } of guardables) {
        const res = await fetch('/api/catalogos/bitacora/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: '010101', id_user: this.usuarioAutenticado, id_presentacion: this.tipoFicha, id_objeto: `${this.obtenerBaseObjeto()}_${pagina}`, comentario: r.comentario || '', estatus: r.estatus === 'correcta' ? 'Aprobado' : 'Requiere correccion' })
        });
        if (!res.ok) { this.abrirModal('Error al guardar', `No se pudo guardar la pagina ${pagina}.`, 'warning'); return; }
      }
      this.revisionesBase = this.clonarRevisiones(this.revisiones);
      this.abrirModal('Guardado exitoso', `Se guardaron ${guardables.length} paginas correctamente.`, 'success');
    } catch { this.abrirModal('Error de conexion', 'Error de conexion al guardar.', 'warning'); }
  }

  async finalizarRevision(): Promise<void> {
    if (!this.pdfSeleccionado || this.numPages <= 0) { this.abrirModal('Sin ficha cargada', 'No hay una ficha cargada.', 'warning'); return; }
    if (!this.usuarioAutenticado) { this.abrirModal('Sesion requerida', 'Inicia sesion nuevamente para generar el reporte.', 'warning'); return; }
    const faltantes = Array.from({ length: this.numPages }, (_, i) => i + 1)
      .filter(p => { const r = this.revisiones[p - 1]; return !(r?.estatus === 'correcta' || r?.estatus === 'correccion'); });

    if (faltantes.length > 0) { this.abrirModal('Paginas pendientes', `Faltan por revisar: ${faltantes.join(', ')}`, 'warning'); return; }

    try {
      const res = await fetch('/api/catalogos/bitacora/reporte-excel/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_user: this.usuarioAutenticado, id_presentacion: this.tipoFicha, id_objeto_base: this.obtenerBaseObjeto(), revisiones: this.revisiones })
      });
      if (!res.ok) { this.abrirModal('Error', 'No se pudo generar el reporte.', 'warning'); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url; enlace.download = `reporte_revision_${this.obtenerBaseObjeto()}.xls`; enlace.click();
      URL.revokeObjectURL(url);
      this.abrirModal('Revision finalizada', 'Se genero el reporte en Excel.', 'success');
    } catch { this.abrirModal('Error de conexion', 'Error al generar el reporte.', 'warning'); }
  }

  descargarPpt(): void {
    if (!this.pptSeleccionado) return;
    const extension = this.pptSeleccionado.toLowerCase().includes('.pptx') ? '.pptx' : '.ppt';
    const enlace = document.createElement('a');
    enlace.href = this.pptSeleccionado;
    enlace.download = `Ficha_Estatal_${this.entidadSeleccionada}${extension}`;
    enlace.click();
  }

  private abrirModal(titulo: string, mensaje: string, tipo: 'info' | 'warning' | 'success' = 'info'): void {
    this.modalRevision = { abierto: true, titulo, mensaje, tipo };
  }

  private async cargarEntidades(): Promise<void> {
    try {
      const res = await fetch('/api/catalogos/entidades/');
      if (res.ok) {
        const payload: unknown = await res.json();
        if (Array.isArray(payload)) {
          const nombres = payload.map(item => this.extraerNombre(item)).filter((n): n is string => Boolean(n));
          if (nombres.length > 0) {
            this.entidades = nombres;
            if (!nombres.includes(this.entidadSeleccionada)) this.entidadSeleccionada = nombres[0];
          }
        }
      }
    } catch { /* fallback */ }

    if (this.tipoFicha === 'estatal') {
      void this.cargarPdfActual();
    }
  }

  private async cargarRevisionesGuardadas(totalPaginas: number): Promise<void> {
    const vacias: RevisionPorPagina[] = Array.from({ length: totalPaginas }, () => ({ estatus: '', comentario: '' }));
    if (!this.pdfSeleccionado || totalPaginas <= 0) { this.revisiones = this.clonarRevisiones(vacias); this.revisionesBase = this.clonarRevisiones(vacias); return; }
    if (!this.usuarioAutenticado) { this.revisiones = this.clonarRevisiones(vacias); this.revisionesBase = this.clonarRevisiones(vacias); return; }
    try {
      const res = await fetch(`/api/catalogos/bitacora/?id_user=${encodeURIComponent(this.usuarioAutenticado)}&id_presentacion=${encodeURIComponent(this.tipoFicha)}&id_objeto_base=${encodeURIComponent(this.obtenerBaseObjeto())}`, { cache: 'no-store' });
      if (!res.ok) { this.revisiones = this.clonarRevisiones(vacias); this.revisionesBase = this.clonarRevisiones(vacias); return; }
      const data: unknown = await res.json();
      const items = (data && typeof data === 'object' && Array.isArray((data as { items?: unknown[] }).items)) ? (data as { items: Array<{ pagina?: number; estatus?: string; comentario?: string }> }).items : [];
      for (const item of items) {
        const pagina = Number(item.pagina);
        if (!Number.isInteger(pagina) || pagina < 1 || pagina > totalPaginas) continue;
        const estatusRaw = String(item.estatus || '').trim().toLowerCase();
        vacias[pagina - 1] = { estatus: estatusRaw === 'aprobado' ? 'correcta' : (estatusRaw.includes('correcci') ? 'correccion' : ''), comentario: String(item.comentario || '') };
      }
      this.revisiones = this.clonarRevisiones(vacias);
      this.revisionesBase = this.clonarRevisiones(vacias);
    } catch { this.revisiones = this.clonarRevisiones(vacias); this.revisionesBase = this.clonarRevisiones(vacias); }
  }

  private obtenerPdfPorEntidad(entidad: string): string | null {
    const clave = this.normalizarClave(entidad);
    return this.pdfFiles.find(f => this.normalizarClave(f.replace('Ficha_Estatal_', '').replace('.pdf', '')) === clave) || null;
  }

  private obtenerPptPorEntidad(entidad: string): string | null {
    const clave = this.normalizarClave(entidad);
    const exacto = this.pptFiles.find(f => this.normalizarClave(f.replace(/\.(ppt|pptx)$/i, '')) === this.normalizarClave(`Ficha_Estatal_${entidad}`));
    if (exacto) return exacto;
    return this.pptFiles.find(f => this.normalizarClave(f.replace(/\.(ppt|pptx)$/i, '')).includes(clave)) || null;
  }

  private obtenerBaseObjeto(): string {
    const nombrePdf = (this.pdfSeleccionado?.split('/').pop() ?? `Ficha_Estatal_${this.entidadSeleccionada}.pdf`).replace(/\?.*$/, '');
    return nombrePdf.replace(/\.pdf$/i, '').replace(/\s+/g, '_');
  }

  private limpiarRevision(): void { this.paginaActual = 1; this.numPages = 0; this.revisiones = []; this.revisionesBase = []; }

  private hayCambiosLocales(): boolean {
    return this.revisiones.some((r, i) => { const b = this.revisionesBase[i] || { estatus: '', comentario: '' }; return r.estatus !== b.estatus || (r.comentario || '') !== (b.comentario || ''); });
  }

  private iniciarRecargaPeriodica(): void {
    if (this.intervaloRecarga !== null) window.clearInterval(this.intervaloRecarga);
    this.intervaloRecarga = window.setInterval(() => {
      if (this.tipoFicha !== 'estatal' || !this.pdfSeleccionado || this.numPages <= 0 || this.hayCambiosLocales()) return;
      void this.cargarRevisionesGuardadas(this.numPages);
    }, 3000);
  }

  private clonarRevisiones(items: RevisionPorPagina[]): RevisionPorPagina[] {
    return items.map(item => ({ estatus: item.estatus, comentario: item.comentario }));
  }

  private normalizarClave(valor: string): string {
    return valor.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  }

  private extraerNombre(item: unknown): string | null {
    if (typeof item === 'string') return item.trim() || null;
    if (item && typeof item === 'object' && 'nombre' in item) {
      const n = (item as { nombre?: unknown }).nombre;
      if (typeof n === 'string') return n.trim() || null;
    }
    return null;
  }

  private readonly actualizarAnchoPdfBound = (): void => { this.actualizarAnchoPdf(); };

  private actualizarAnchoPdf(): void {
    const c = this.visorPdfRef?.nativeElement ?? null;
    if (!c) return;
    this.pdfWidth = Math.max(300, Math.min(504, c.clientWidth - 16));
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
      const response = await fetch(rutaPdf);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const pdfBlob = await response.blob();

      const arrayBuffer = await pdfBlob.arrayBuffer();
      const loadingTask = getDocument({
        data: new Uint8Array(arrayBuffer),
        disableWorker: true
      } as any);
      this.pdfDoc = await loadingTask.promise;

      this.ngZone.run(() => {
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
    if (!this.pdfDoc || !this.pdfCanvasRef?.nativeElement || this.paginaActual < 1 || this.paginaActual > this.numPages) {
      return;
    }

    try {
      const pagina = await this.pdfDoc.getPage(this.paginaActual);
      const viewportBase = pagina.getViewport({ scale: 1 });
      const anchoDisponible = Math.max(300, this.pdfWidth);
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

      this.renderTask = pagina.render({ canvasContext: context, viewport });
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
}
