import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'app-header',
  standalone: true,
  templateUrl: './header.component.html',
  styleUrl: './header.component.css'
})
export class HeaderComponent {
  @Input() menuAbierto = false;
  @Output() toggleMenu = new EventEmitter<void>();

  alternarMenu(): void {
    this.toggleMenu.emit();
  }
}

