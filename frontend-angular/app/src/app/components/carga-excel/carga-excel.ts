import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { CargaExcelService } from './carga-excel.service';
import { Area, Tema, DiccionarioCampo } from '../../services/types';
import { ChangeDetectorRef } from '@angular/core';
import { NgZone } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-carga-excel',
  standalone: true,
  templateUrl: './carga-excel.html',
  imports: [CommonModule, FormsModule],
})
export class CargaExcelComponent implements OnInit, OnDestroy {
  private service = inject(CargaExcelService);
  private cdr = inject(ChangeDetectorRef);
  private zone = inject(NgZone);

  @ViewChild('fileInput') fileInput?: ElementRef<HTMLInputElement>;

  private temasSubscription?: Subscription;
  private diccionarioSubscription?: Subscription;
  private hojasSubscription?: Subscription;
  private cargaSubscription?: Subscription;
  private progressInterval: ReturnType<typeof setInterval> | null = null;

  areas: Area[] = [];
  temas: Tema[] = [];
  diccionario: DiccionarioCampo[] = [];

  idArea: number | null = null;
  idTema: number | null = null;

  archivo: File | null = null;
  mensaje = '';
  isLoading = false;
  progress = 0;

  hojas: string[] = [];
  hojaSeleccionada = '';

  ngOnInit() {
    this.service.getAreas().subscribe({
      next: (data) => {
        // 1. Asignamos los datos
        this.areas = data;
        // 2. Avisamos a Angular que revise la vista inmediatamente
        this.cdr.detectChanges();
        console.log('ÁREAS renderizando:', this.areas);
      },
      error: (error) => {
        this.mensaje = 'Error al cargar áreas';
        this.cdr.detectChanges();
      },
    });
  }

  onAreaChange(value: string) {
    this.idArea = value ? Number(value) : null;
    this.idTema = null;
    this.temas = [];
    this.diccionario = [];
    this.temasSubscription?.unsubscribe();
    this.diccionarioSubscription?.unsubscribe();
    this.reiniciarEstadoCarga();

    if (this.idArea) {
      this.temasSubscription = this.service.getTemas(this.idArea).subscribe({
        next: (data) => {
          this.zone.run(() => {
            this.temas = data;
            console.log('Temas cargados:', this.temas);
            this.cdr.detectChanges();
          });
        },
        error: (error) => {
          console.error('Error al cargar temas:', error);
          this.mensaje = 'Error al cargar temas';
          this.cdr.detectChanges();
        },
      });
    }
  }

  onTemaChange(value: string) {
    this.idTema = value ? Number(value) : null;
    this.diccionario = [];
    this.diccionarioSubscription?.unsubscribe();
    this.reiniciarEstadoCarga();

    if (!this.idTema) {
      return;
    }

    this.diccionarioSubscription = this.service.getDiccionario(this.idTema).subscribe({
      next: (data) => {
        this.diccionario = data;
        this.cdr.detectChanges();
      },
      error: () => {
        this.mensaje = 'Error al cargar diccionario';
        this.cdr.detectChanges();
      },
    });
  }

  onFileChange(event: any) {
    const file = event.target.files?.[0];
    this.reiniciarEstadoCarga(false);
    if (!file) return;

    this.archivo = file;

    this.hojasSubscription = this.service.obtenerHojas(file).subscribe({
      next: (data) => {
        this.hojas = data.hojas || [];
        this.cdr.detectChanges();
      },
      error: () => {
        this.mensaje = 'Error al leer hojas';
        this.cdr.detectChanges();
      },
    });
  }

  onSubmit() {
    if (
      this.isLoading ||
      !this.archivo ||
      !this.idTema ||
      !this.idArea
    ) return;

    if (!this.hojaSeleccionada) {
      this.mensaje = 'Seleccione una hoja';
      this.cdr.detectChanges();
      return;
    }

    this.isLoading = true;
    this.progress = 0;

    let value = 0;

    this.limpiarIntervaloProgreso();
    this.progressInterval = setInterval(() => {
      value += Math.random() * 15;
      if (value >= 90) value = 90;
      this.progress = Math.floor(value);
      this.cdr.detectChanges();
    }, 300);

    this.cargaSubscription = this.service
      .subirExcel(this.idArea, this.idTema, this.archivo, this.hojaSeleccionada)
      .subscribe({
        next: (data) => {
          this.limpiarIntervaloProgreso();

          this.progress = 100;

          this.mensaje =
            `Archivo validado y guardado correctamente.\n` +
            `Registros: ${data.total_registros}\n` +
            `Archivo: ${data.archivo}\n` +
            `Carpeta OneDrive: ${data.carpeta}`;

          this.isLoading = false;
          this.cdr.detectChanges();
        },

        error: (err) => {
          this.limpiarIntervaloProgreso();

          console.log('ERROR COMPLETO:', err);

          const errorData = err.error;

          if (errorData?.error === 'Estructura de columnas inválida') {
            const faltantes = errorData.faltantes?.join(', ') || 'Ninguno';

            const extras = errorData.extras?.join(', ') || 'Ninguno';

            this.mensaje =
              `Columnas inválidas\n` + `Faltantes: ${faltantes}\n` + `Extras: ${extras}`;
          } else if (errorData?.detalle?.length) {
            const detalles = errorData.detalle.map(
              (e: any) => `Fila ${e.fila}, columna ${e.columna}: ${e.error}`,
            );

            this.mensaje = `${errorData.error}\n` + detalles.join('\n');
          } else {
            this.mensaje = errorData?.error || 'Error al enviar archivo';
          }

          this.isLoading = false;
          this.cdr.detectChanges();
        },
      });
  }

  private reiniciarEstadoCarga(limpiarInputArchivo = true): void {
    this.hojasSubscription?.unsubscribe();
    this.cargaSubscription?.unsubscribe();
    this.hojasSubscription = undefined;
    this.cargaSubscription = undefined;
    this.limpiarIntervaloProgreso();

    this.archivo = null;
    this.hojas = [];
    this.hojaSeleccionada = '';
    this.progress = 0;
    this.mensaje = '';
    this.isLoading = false;

    if (limpiarInputArchivo && this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
  }

  private limpiarIntervaloProgreso(): void {
    if (this.progressInterval !== null) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
  }

  ngOnDestroy(): void {
    this.temasSubscription?.unsubscribe();
    this.diccionarioSubscription?.unsubscribe();
    this.hojasSubscription?.unsubscribe();
    this.cargaSubscription?.unsubscribe();
    this.limpiarIntervaloProgreso();
  }
}
