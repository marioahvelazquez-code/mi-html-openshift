import { CommonModule } from '@angular/common';
import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

interface EntidadOpcion {
  clave: string;
  nombre: string;
}

const ENTIDADES: EntidadOpcion[] = [
  { clave: '01', nombre: 'Aguascalientes' },
  { clave: '02', nombre: 'Baja California' },
  { clave: '03', nombre: 'Baja California Sur' },
  { clave: '04', nombre: 'Campeche' },
  { clave: '05', nombre: 'Coahuila' },
  { clave: '06', nombre: 'Colima' },
  { clave: '07', nombre: 'Chiapas' },
  { clave: '08', nombre: 'Chihuahua' },
  { clave: '09', nombre: 'Ciudad de México' },
  { clave: '10', nombre: 'Durango' },
  { clave: '11', nombre: 'Guanajuato' },
  { clave: '12', nombre: 'Guerrero' },
  { clave: '13', nombre: 'Hidalgo' },
  { clave: '14', nombre: 'Jalisco' },
  { clave: '15', nombre: 'México' },
  { clave: '16', nombre: 'Michoacán' },
  { clave: '17', nombre: 'Morelos' },
  { clave: '18', nombre: 'Nayarit' },
  { clave: '19', nombre: 'Nuevo León' },
  { clave: '20', nombre: 'Oaxaca' },
  { clave: '21', nombre: 'Puebla' },
  { clave: '22', nombre: 'Querétaro' },
  { clave: '23', nombre: 'Quintana Roo' },
  { clave: '24', nombre: 'San Luis Potosí' },
  { clave: '25', nombre: 'Sinaloa' },
  { clave: '26', nombre: 'Sonora' },
  { clave: '27', nombre: 'Tabasco' },
  { clave: '28', nombre: 'Tamaulipas' },
  { clave: '29', nombre: 'Tlaxcala' },
  { clave: '30', nombre: 'Veracruz' },
  { clave: '31', nombre: 'Yucatán' },
  { clave: '32', nombre: 'Zacatecas' },
];

@Component({
  standalone: true,
  selector: 'app-ficha-presidencial',
  templateUrl: './ficha-presidencial.html',
  styleUrl: './ficha-presidencial.css',
  imports: [CommonModule, FormsModule, LucideAngularModule],
})
export class FichaPresidencialComponent implements OnDestroy {
  entidades = ENTIDADES;
  claveEntidad = ENTIDADES[0].clave;
  mensaje = '';
  cargando = false;
  archivoDescarga = '';

  get entidadSeleccionada(): EntidadOpcion | undefined {
    return this.entidades.find((entidad) => entidad.clave === this.claveEntidad);
  }

  ngOnDestroy(): void {
  }

  generarLote(): void {
    this.cargando = true;
    this.mensaje = 'Generando las 32 fichas presidenciales...';

    const urlDescarga = 'http://localhost:8088/api/catalogos/getGeneraFichaPresidencialLote/';
    const enlace = document.createElement('a');
    enlace.href = urlDescarga;
    enlace.style.display = 'none';
    document.body.appendChild(enlace);

    this.mensaje = 'La descarga del lote de 32 fichas va a iniciar.';
    this.cargando = false;

    window.setTimeout(() => {
      enlace.click();
      enlace.remove();
    }, 0);
  }

  generarUna(): void {
    const clave = this.claveEntidad.trim();
    if (!clave) {
      this.mensaje = 'Selecciona una entidad antes de generar una ficha.';
      return;
    }

    this.cargando = true;
    this.mensaje = `Generando la ficha de ${this.entidadSeleccionada?.nombre} (${clave})...`;

    const urlDescarga = `http://localhost:8088/api/catalogos/getGeneraFichaPresidencial/?cveEntidad=${encodeURIComponent(clave)}`;
    const enlace = document.createElement('a');
    enlace.href = urlDescarga;
    enlace.style.display = 'none';
    document.body.appendChild(enlace);

    this.mensaje = `Descarga iniciada para ${this.entidadSeleccionada?.nombre}.`;
    this.cargando = false;

    window.setTimeout(() => {
      enlace.click();
      enlace.remove();
    }, 0);
  }
}