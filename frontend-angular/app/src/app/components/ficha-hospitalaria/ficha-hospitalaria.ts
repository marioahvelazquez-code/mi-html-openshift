import { Component, ElementRef, NgZone, OnInit, ViewChild, inject } from '@angular/core';

import { CommonModule } from '@angular/common';
import { fichahospitalaria } from '../../services/ficha-hospitalaria';
import { Region, Entidad, NivelAtencion, UnidadMedica } from '../../services/types';
import { ChangeDetectorRef } from '@angular/core';

import { FormsModule } from '@angular/forms';
import { GlobalWorkerOptions, getDocument, PDFDocumentProxy, RenderTask } from 'pdfjs-dist';

@Component({
  selector: 'app-ficha-hospitalaria',
  standalone: true,
  templateUrl: './ficha-hospitalaria.html',
  styleUrls: ['./ficha-hospitalaria.css'],
  imports: [CommonModule, FormsModule],
})
export class FichaHospitalaria implements OnInit {
  private service = inject(fichahospitalaria);
  private cdr = inject(ChangeDetectorRef);
  private zone = inject(NgZone);
  private pdfDoc: PDFDocumentProxy | null = null;
  private renderTask: RenderTask | null = null;
  @ViewChild('visorPdfRef') visorPdfRef?: ElementRef<HTMLElement>;
  @ViewChild('pdfCanvasRef') pdfCanvasRef?: ElementRef<HTMLCanvasElement>;

  constructor(private readonly ngZone: NgZone) {}

  region: Region[] = [];
  entidad: Entidad[] = [];
  nivelAtencion: NivelAtencion[] = [];
  unidadMedica: UnidadMedica[] = [];

  idRegion: string | null = null;
  idEntidad: string | null = null;
  id_nivel_atencion: string | null = null;
  id_unidad_medica: string | null = null;
  archivoGenerado: string | null = null;
  archivoDescarga: string | null = null;
  paginaActual = 1;
  numPages = 0;
  pdfWidth = 900;
  modalRevision = {
    abierto: false,
    titulo: '',
    mensaje: '',
    tipo: 'info' as 'info' | 'warning' | 'success',
  };

  mensaje = '';
  isLoading = false;
  progress = 0;

  get totalPaginasVisual(): number {
    return Math.max(this.numPages);
  }
  get paginadorCargando(): boolean {
    return Boolean(this.archivoGenerado) && this.totalPaginasVisual === 0;
  }
  get paginaActualVisual(): number {
    if (!this.archivoGenerado || this.totalPaginasVisual === 0) return 0;
    return Math.max(1, Math.min(this.paginaActual, this.totalPaginasVisual));
  }

  limpiar() {
    this.idRegion = null;
    this.idEntidad = null;
    this.id_nivel_atencion = null;
    this.id_unidad_medica = null;
    this.archivoGenerado = null;
    this.archivoDescarga = null;
    this.paginaActual = 1;
    this.numPages = 0;
    this.mensaje = '';
    this.isLoading = false;
    this.progress = 0;
    this.cdr.detectChanges();
  }
  ngOnInit() {
    GlobalWorkerOptions.workerSrc = '/assets/pdf.worker.min.mjs';
    this.service.getRegion().subscribe({
      next: (data) => {
        // 1. Asignamos los datos
        this.region = data;
        // 2. Avisamos a Angular que revise la vista inmediatamente
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.mensaje = 'Error al cargar Regiones';
        this.cdr.detectChanges();
      },
    });
  }
  descargarPpt(): void {
    if (!this.archivoDescarga) return;
    const extension = this.archivoDescarga.toLowerCase().includes('.pptx') ? '.pptx' : '.ppt';
    const enlace = document.createElement('a');
    enlace.href = this.archivoDescarga;
    enlace.download = `${this.archivoDescarga}`;
    enlace.click();
  }
  async onRegionChange(value: string) {
    this.idRegion = value ? String(value) : null;
    this.idEntidad = null;
    this.id_nivel_atencion = null;
    this.id_unidad_medica = null;
    this.mensaje = '';

    if (this.idRegion) {
      try {
        this.service.getEntidad(this.idRegion).subscribe((data) => {
          this.zone.run(() => {
            this.entidad = data;

            this.cdr.detectChanges();
          });
        });
      } catch (error) {
        this.mensaje = 'Error al cargar entidades';
        this.cdr.detectChanges();
      }
    } else {
      this.entidad = [];
    }
  }

  onEntidadChange(value: string) {
    this.idEntidad = value ? String(value) : null;
    this.id_nivel_atencion = null;
    this.id_unidad_medica = null;
    this.mensaje = '';

    if (!this.idEntidad) {
      return;
    }

    this.service.getNivelAtencion(this.idEntidad).subscribe({
      next: (data) => {
        this.nivelAtencion = data;

        this.cdr.detectChanges();
      },
      error: () => {
        this.mensaje = 'Error al cargar nivel de atención';
        this.cdr.detectChanges();
      },
    });
  }

  onNivelAtencionChange(value: string) {
    this.id_nivel_atencion = value ? String(value) : null;
    this.id_unidad_medica = null;
    this.mensaje = '';

    if (!this.id_nivel_atencion || !this.idEntidad) {
      return;
    }

    this.service.getUnidad(this.idEntidad, this.id_nivel_atencion).subscribe({
      next: (data) => {
        this.unidadMedica = data;

        this.cdr.detectChanges();
      },
      error: () => {
        this.mensaje = 'Error al cargar nivel de atención';
        this.cdr.detectChanges();
      },
    });
  }

  onUnidadMedicaChange(value: string) {
    this.id_unidad_medica = value ? String(value) : null;
  }

  private abrirModal(
    titulo: string,
    mensaje: string,
    tipo: 'info' | 'warning' | 'success' = 'info',
  ): void {
    this.modalRevision = { abierto: true, titulo, mensaje, tipo };
  }
  onDocumentLoadError(): void {
    this.numPages = 0;
    this.abrirModal(
      'Error al cargar la ficha',
      'No se pudo cargar el PDF seleccionado.',
      'warning',
    );
  }

  siguiente(): void {
    if (!this.archivoGenerado || this.paginaActual >= this.numPages) {
      return;
    }

    this.paginaActual += 1;
    this.cdr.detectChanges();
    void this.renderizarPaginaActual();
  }

  anterior(): void {
    if (!this.archivoGenerado || this.paginaActual <= 1) {
      return;
    }

    this.paginaActual -= 1;
    this.cdr.detectChanges();
    void this.renderizarPaginaActual();
  }

  private async renderizarPaginaActual(): Promise<void> {
    const canvas = this.pdfCanvasRef!.nativeElement;

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

      const canvas = this.pdfCanvasRef.nativeElement;

      const context = canvas.getContext('2d');

      if (!context) return;

      // ancho REAL del contenedor
      const contenedor = this.visorPdfRef?.nativeElement;

      const anchoDisponible = contenedor?.clientWidth || 800;

      // viewport base
      const viewportBase = pagina.getViewport({ scale: 1 });

      // escala dinámica
      const escala = anchoDisponible / viewportBase.width;

      const viewport = pagina.getViewport({ scale: escala });

      // tamaño interno real del canvas
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      // tamaño visual CSS
      canvas.style.width = '100%';
      canvas.style.height = 'auto';
      canvas.style.display = 'block';

      if (this.renderTask) {
        await this.renderTask.cancel();

        this.renderTask = null;
      }

      context.clearRect(0, 0, canvas.width, canvas.height);

      this.renderTask = pagina.render({
        canvas,
        viewport,
      });

      await this.renderTask.promise;

      this.renderTask = null;
    } catch (error) {
      console.error(error);

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
  private async cargarPdfActual(rutaPdf: string): Promise<void> {
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
      });

      this.pdfDoc = await loadingTask.promise;

      this.ngZone.run(() => {
        this.numPages = this.pdfDoc?.numPages ?? 0;
        this.paginaActual = 1;
        this.cdr.detectChanges();
      });
      console.log('Cargando PDF desde 4:', this.pdfDoc);
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      await this.renderizarPaginaActual();
    } catch (error) {
      console.error('ERROR CARGANDO PDF:', error);
      await this.liberarDocumentoPdf();
      this.ngZone.run(() => this.onDocumentLoadError());
    }
  }

  onSubmit() {
    if (!this.idRegion || !this.idEntidad || !this.id_nivel_atencion || !this.id_unidad_medica)
      return;

    this.isLoading = true;
    this.progress = 0;

    let value = 0;

    const interval = setInterval(() => {
      const incremento = (90 - value) * 0.02;

      value += incremento;

      if (value >= 90) {
        value = 90;
      }

      this.progress = Math.floor(value);
      this.cdr.detectChanges();
    }, 500);

    this.service.getFichaHospitalaria(this.id_unidad_medica).subscribe({
      next: (data) => {
        clearInterval(interval);
        this.progress = 100;
        this.mensaje = 'Ficha hospitalaria cargada exitosamente';
        if (data.url) {
          const urlPdf = `/${data.url.replace(/^\/+/, '')}`;
          const urlPptx = data.pptx_url ? `/${data.pptx_url.replace(/^\/+/, '')}` : urlPdf;
          console.log('Cargando PDF desde:', urlPdf);
          this.archivoGenerado = urlPdf;
          this.archivoDescarga = urlPptx;
          this.cargarPdfActual(urlPdf);
        }
        this.cdr.detectChanges();
      },
      error: () => {
        clearInterval(interval);
        this.progress = 0;
        this.mensaje = 'Error al cargar ficha hospitalaria';
        this.cdr.detectChanges();
      },
    });
  }
}
