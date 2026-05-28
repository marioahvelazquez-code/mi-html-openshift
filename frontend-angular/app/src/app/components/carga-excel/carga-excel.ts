import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CargaExcelService } from './carga-excel.service';
import { Area, Tema, DiccionarioCampo } from '../../services/types';
import { ChangeDetectorRef } from '@angular/core';
import { NgZone } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-carga-excel',
  standalone: true,
  templateUrl: './carga-excel.html',
  imports: [CommonModule, FormsModule],
})
export class CargaExcelComponent implements OnInit {
  private service = inject(CargaExcelService);
  private cdr = inject(ChangeDetectorRef);
  private zone = inject(NgZone);

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

  async onAreaChange(value: string) {
    this.idArea = value ? Number(value) : null;
    this.idTema = null;
    this.archivo = null;
    this.diccionario = [];
    this.mensaje = '';

    if (this.idArea) {
      try {
        this.service.getTemas(this.idArea).subscribe((data) => {
          this.zone.run(() => {
            this.temas = data;
            console.log('Temas cargados:', this.temas);
            this.cdr.detectChanges();
          });
        });
      } catch (error) {
        console.error('Error al cargar temas:', error);
        this.mensaje = 'Error al cargar temas';
        this.cdr.detectChanges();
      }
    } else {
      this.temas = [];
    }
  }

  onTemaChange(value: string) {
    this.idTema = value ? Number(value) : null;

    if (!this.idTema) {
      this.diccionario = [];
      return;
    }

    this.service.getDiccionario(this.idTema).subscribe({
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
    if (!file) return;

    this.archivo = file;

    this.service.obtenerHojas(file).subscribe({
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
    if (!this.archivo || !this.idTema || !this.idArea) return;

    if (!this.hojaSeleccionada) {
      this.mensaje = 'Seleccione una hoja';
      this.cdr.detectChanges();
      return;
    }

    this.isLoading = true;
    this.progress = 0;

    let value = 0;

    const interval = setInterval(() => {
      value += Math.random() * 15;
      if (value >= 90) value = 90;
      this.progress = Math.floor(value);
      this.cdr.detectChanges();
    }, 300);

    this.service
      .subirExcel(this.idArea, this.idTema, this.archivo, this.hojaSeleccionada)
      .subscribe({
        next: (data) => {
          clearInterval(interval);
          this.progress = 100;
          this.mensaje = `Archivo cargado con ${data.total_registros} registros`;
          this.isLoading = false;
          this.cdr.detectChanges();
        },
        error: (err) => {
          clearInterval(interval);

          console.log('ERROR COMPLETO:', err);

          const errorData = err.error;

          if (errorData?.error === 'Estructura de columnas inválida') {
            const faltantes = errorData.faltantes?.join(', ') || 'Ninguno';
            const extras = errorData.extras?.join(', ') || 'Ninguno';

            this.mensaje = ` Columnas inválidas
          Faltantes: ${faltantes}
          Extras: ${extras}`;
          } else {
            this.mensaje = errorData?.error || 'Error al enviar archivo';
          }

          this.isLoading = false;
          this.cdr.detectChanges();
        },
      });
  }
}
