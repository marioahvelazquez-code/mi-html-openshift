import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { LucideAngularModule } from 'lucide-angular';
import { catchError, finalize, of, timeout } from 'rxjs';

interface CortesInformacionResponse {
  ok: boolean;
  total?: number;
  items?: Record<string, unknown>[];
}

@Component({
  selector: 'app-cortes-informacion',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  templateUrl: './cortes-informacion.html',
  styleUrl: './cortes-informacion.css',
})
export class CortesInformacionComponent implements OnInit {
  readonly columnas = [
    { campo: 'id_tema', etiqueta: 'Id tema' },
    { campo: 'tema', etiqueta: 'Tema' },
    { campo: 'fuente', etiqueta: 'Fuente' },
    { campo: 'periodo', etiqueta: 'Periodo' },
    { campo: 'fecha_de_corte', etiqueta: 'Fecha de corte' },
    { campo: 'anio', etiqueta: 'Año' },
    { campo: 'numero_mes', etiqueta: '# Mes' },
    { campo: 'mes', etiqueta: 'Mes' },
    { campo: 'semana', etiqueta: 'Semana' },
    { campo: 'periodo_historico', etiqueta: 'Periodo histórico' },
  ];

  readonly cargando = signal(true);
  readonly totalRegistros = signal(0);
  readonly filasTabla = signal<Record<string, unknown>[]>([]);
  private readonly rutaCsv = '/assets/corte.csv';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.cargarCortes();
  }

  private cargarCortes(): void {
    this.cargando.set(true);

    this.http
      .get(this.rutaCsv, { responseType: 'text' })
      .pipe(
        timeout(15000),
        catchError(() => of('')),
        finalize(() => this.cargando.set(false)),
      )
      .subscribe((contenido) => {
        const items = this.parsearCsv(contenido as string);
        this.totalRegistros.set(items.length);
        this.filasTabla.set(items);
      });
  }

  private parsearCsv(contenido: string): Record<string, unknown>[] {
    const lineas = contenido
      .split(/\r?\n/)
      .map((linea) => linea.trim())
      .filter((linea) => linea.length > 0);

    return lineas.map((linea) => {
      const columnas = this.dividirCsv(linea);
      return {
        id_tema: columnas[0] ?? '',
        tema: columnas[1] ?? '',
        fuente: columnas[2] ?? '',
        periodo: columnas[3] ?? '',
        fecha_de_corte: columnas[4] ?? '',
        anio: columnas[5] ?? '',
        numero_mes: columnas[6] ?? '',
        mes: columnas[7] ?? '',
        semana: columnas[8] ?? '',
        periodo_historico: columnas[9] ?? '',
      };
    });
  }

  private dividirCsv(linea: string): string[] {
    const columnas: string[] = [];
    let valorActual = '';
    let dentroDeComillas = false;

    for (let indice = 0; indice < linea.length; indice += 1) {
      const caracter = linea[indice];
      const siguiente = linea[indice + 1];

      if (caracter === '"' && dentroDeComillas && siguiente === '"') {
        valorActual += '"';
        indice += 1;
        continue;
      }

      if (caracter === '"') {
        dentroDeComillas = !dentroDeComillas;
        continue;
      }

      if (caracter === ',' && !dentroDeComillas) {
        columnas.push(valorActual);
        valorActual = '';
        continue;
      }

      valorActual += caracter;
    }

    columnas.push(valorActual);
    return columnas.map((valor) => valor.trim());
  }

  valorFila(fila: Record<string, unknown>, campo: string): string {
    const valor = fila[campo];
    if (valor === null || valor === undefined) {
      return '';
    }
    if (typeof valor === 'string') {
      return valor;
    }
    if (valor instanceof Date) {
      return valor.toISOString();
    }
    return String(valor);
  }

  claseCelda(campo: string): string {
    if (campo === 'id_tema' || campo === 'anio' || campo === 'numero_mes' || campo === 'semana') {
      return 'celda-numero';
    }

    if (campo === 'fecha_de_corte') {
      return 'celda-fecha';
    }

    if (campo === 'fuente') {
      return 'celda-fuente';
    }

    if (campo === 'periodo' || campo === 'periodo_historico') {
      return 'celda-periodo';
    }

    return '';
  }

  valorFormateado(fila: Record<string, unknown>, campo: string): string {
    const valor = this.valorFila(fila, campo);

    if (campo !== 'fecha_de_corte' || !valor) {
      return valor;
    }

    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) {
      return valor;
    }

    return new Intl.DateTimeFormat('es-MX', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(fecha);
  }
}
