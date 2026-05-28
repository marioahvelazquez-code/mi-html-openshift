import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { form } from '@angular/forms/signals';

@Component({
  selector: 'app-excel',
  imports: [FormsModule],
  templateUrl: './excel.html',
  styleUrl: './excel.css',
})
export class Excel {
  Exceles: string[] = [];
  nuevoExcel: string = '';

  agregarExcel() {
    if (this.nuevoExcel.trim() !== '') {
      this.Exceles.push(this.nuevoExcel.trim());
      this.nuevoExcel = '';
    }
  }
}
