import { Component, OnInit, inject } from '@angular/core';
import { BitacoraService } from './bitacora.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef } from '@angular/core';

@Component({
  standalone: true,
  selector: 'app-bitacora',
  templateUrl: './bitacora.html',
  styleUrls: ['./bitacora.css'],
  imports: [FormsModule, CommonModule],
})
export class BitacoraComponent implements OnInit {
  private cdr = inject(ChangeDetectorRef);
  registros: any[] = [];
  registrosFiltrados: any[] = [];

  areas: any[] = [];
  areaSeleccionada: string = '';

  constructor(private bitacoraService: BitacoraService) {}

  ngOnInit(): void {
    this.cargarAreas();
    this.cargarBitacora();
  }

  cargarBitacora() {
    this.bitacoraService.getBitacora().subscribe((data) => {
      this.registros = data;
      this.registrosFiltrados = data;

      this.cdr.detectChanges();
    });
  }

  cargarAreas() {
    this.bitacoraService.getAreas().subscribe((data) => {
      this.areas = data;
      this.cdr.detectChanges();
    });
  }

  filtrarPorArea() {
    if (!this.areaSeleccionada) {
      this.registrosFiltrados = this.registros;
    } else {
      this.registrosFiltrados = this.registros.filter(
        (r) => r.nombre_area === this.areaSeleccionada,
      );
    }
  }
}
