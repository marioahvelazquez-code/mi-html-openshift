import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-header',
  templateUrl: './header.html',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
})
export class HeaderComponent {
  @Input() showMenu: boolean = false;
  @Input() showHamburger: boolean = true; // controla visibilidad
  @Input() menuOpen: boolean = false; // controla icono

  @Output() openMenu = new EventEmitter<void>();

  onOpenMenu() {
    this.openMenu.emit();
  }
}
