import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChatbotRequest {
  pregunta: string;
}

export interface ChatbotResponse {
  respuesta?: string;
  error?: string;
}

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private apiUrl = '/api/catalogos';

  constructor(private http: HttpClient) {}

  preguntar(pregunta: string): Observable<ChatbotResponse> {
    const payload: ChatbotRequest = { pregunta };
    return this.http.post<ChatbotResponse>(`${this.apiUrl}/chatbot/`, payload);
  }
}
