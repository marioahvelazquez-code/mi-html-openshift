import { Component } from '@angular/core';
import { ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';
import { firstValueFrom, timeout } from 'rxjs';
import { ChatbotService } from '../../services/chatbot';

@Component({
  standalone: true,
  selector: 'app-chatbot',
  templateUrl: './chatbot.html',
  styleUrl: './chatbot.css',
  imports: [CommonModule, FormsModule, LucideAngularModule],
})
export class ChatbotComponent {
  pregunta = '';
  respuesta = '';
  loading = false;
  error = '';

  constructor(
    private chatbotService: ChatbotService,
    private cdr: ChangeDetectorRef,
  ) {}

  async enviarPregunta() {
    const preguntaLimpia = this.pregunta.trim();
    if (!preguntaLimpia || this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.respuesta = '';
    this.cdr.detectChanges();
    console.log('[Chatbot] Enviando pregunta:', preguntaLimpia);

    const safetyTimer = setTimeout(() => {
      if (this.loading) {
        this.loading = false;
        if (!this.error) {
          this.error = 'La consulta no finalizó correctamente. Intenta de nuevo.';
        }
        this.cdr.detectChanges();
        console.warn('[Chatbot] Safety timer liberó estado de carga');
      }
    }, 25000);

    try {
      const resp = await firstValueFrom(
        this.chatbotService.preguntar(preguntaLimpia).pipe(timeout(20000)),
      );

      console.log('[Chatbot] Respuesta recibida:', resp);

      this.respuesta = String(resp?.respuesta || '').trim();
      if (!this.respuesta) {
        this.error = String(resp?.error || 'No se recibió una respuesta del asistente.');
      }
    } catch (err: any) {
      console.error('[Chatbot] Error al consultar:', err);
      if (err?.name === 'TimeoutError') {
        this.error = 'El chatbot tardó demasiado en responder. Intenta de nuevo.';
      } else {
        this.error =
          err?.error?.error || err?.error?.detail || 'Ocurrió un error al consultar el chatbot.';
      }
    } finally {
      clearTimeout(safetyTimer);
      this.loading = false;
      this.cdr.detectChanges();
      console.log('[Chatbot] Finalizó consulta');
    }
  }
}
