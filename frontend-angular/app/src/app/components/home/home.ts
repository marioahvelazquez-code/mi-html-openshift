import { Component } from '@angular/core';
import { CarruselHomeComponent } from '../carrusel-home/carrusel-home';

@Component({
  selector: 'app-home',
  imports: [CarruselHomeComponent],
  templateUrl: './home.html',
  styleUrl: './home.css',
})
export class Home {}
